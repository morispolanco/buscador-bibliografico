import streamlit as st
import requests
from urllib.parse import quote
import re
import time

# Función para generar cita en formato APA
def format_apa_citation(title, authors, year, journal, doi, url):
    # Construir la cadena de autores
    if not authors:
        authors_str = ''
    else:
        authors_formatted = []
        for author in authors:
            # Formato: Apellido, Inicial del nombre.
            name_parts = author.split()
            if len(name_parts) > 1:
                last_name = name_parts[-1]
                initials = ''.join([f'{n[0]}.' for n in name_parts[:-1]])
                authors_formatted.append(f'{last_name}, {initials}')
            else:
                authors_formatted.append(author)
        if len(authors_formatted) == 1:
            authors_str = authors_formatted[0]
        elif len(authors_formatted) <= 7:
            authors_str = ', '.join(authors_formatted[:-1]) + ', & ' + authors_formatted[-1]
        else:
            authors_str = ', '.join(authors_formatted[:6]) + ', ... ' + authors_formatted[-1]
    
    # Construir la cita APA
    citation_parts = []
    if authors_str:
        citation_parts.append(authors_str)
    if year:
        citation_parts.append(f'({year}).')
    if title:
        citation_parts.append(title + '.')
    if journal:
        citation_parts.append(journal + '.')
    
    # Agregar DOI o URL
    if doi:
        citation_parts.append(f'https://doi.org/{doi}')
    elif url:
        citation_parts.append(url)
    
    return ' '.join(citation_parts)

# Función para procesar la consulta y manejar frases entre comillas
def process_query(query):
    # Expresión regular para encontrar frases entre comillas
    quoted_phrases = re.findall(r'"([^"]*)"', query)
    
    # Reemplazar las frases entre comillas con marcadores temporales
    temp_query = re.sub(r'"[^"]*"', '###PHRASE###', query)
    
    # Dividir el resto en palabras individuales
    words = re.findall(r'\b\w+\b', temp_query)
    
    # Reconstruir la consulta procesada
    processed_terms = []
    phrase_index = 0
    
    for term in re.split(r'(\s+)', query):
        if term.strip() == '###PHRASE###':
            if phrase_index < len(quoted_phrases):
                processed_terms.append(f'"{quoted_phrases[phrase_index]}"')
                phrase_index += 1
        elif term.strip():
            # Agregar palabras individuales
            processed_terms.extend(re.findall(r'\b\w+\b', term))
    
    # Unir todos los términos con AND
    return ' AND '.join(processed_terms)

# Función para consultar la API CrossRef con reintentos
def query_crossref(query, rows=10, max_retries=3):
    # Procesar la consulta para manejar frases entre comillas
    processed_query = process_query(query)
    
    base_url = 'https://api.crossref.org/works'
    params = {
        'query': processed_query,  # Usamos 'query' en lugar de 'query.bibliographic'
        'rows': rows,
        'filter': 'has-full-text:true'
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.get(
                base_url, 
                params=params, 
                timeout=15,
                headers={'User-Agent': 'AcademicSearchApp/1.0 (mailto:your-email@example.com)'}
            )
            response.raise_for_status()
            data = response.json()
            items = data.get('message', {}).get('items', [])
            results = []
            
            for item in items:
                title_list = item.get('title', [])
                title = title_list[0] if title_list else ''
                
                # Procesar autores
                authors = []
                for author in item.get('author', []):
                    given = author.get('given', '').strip()
                    family = author.get('family', '').strip()
                    if family and given:
                        authors.append(f'{given} {family}')
                    elif family:
                        authors.append(family)
                    elif given:
                        authors.append(given)
                
                # Obtener año de publicación
                year = None
                published_dates = item.get('published-print', {}).get('date-parts', []) or \
                                 item.get('published-online', {}).get('date-parts', [])
                if published_dates:
                    year = published_dates[0][0]
                
                # Obtener revista
                journal = ''
                container_titles = item.get('container-title', [])
                if container_titles:
                    journal = container_titles[0]
                
                doi = item.get('DOI', '')
                
                # Obtener URL (priorizar PDF)
                url = ''
                for link in item.get('link', []):
                    if link.get('content-type') == 'application/pdf':
                        url = link.get('URL', '')
                        break
                if not url:
                    url = item.get('URL', '')
                
                citation = format_apa_citation(title, authors, year, journal, doi, url)
                results.append({
                    'title': title,
                    'authors': authors,
                    'year': year,
                    'journal': journal,
                    'doi': doi,
                    'url': url,
                    'citation': citation
                })
            return results
            
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                st.warning(f"Intento {attempt + 1} fallido. Reintentando en 2 segundos...")
                time.sleep(2)
                continue
            else:
                st.error("La consulta está tardando demasiado. Por favor, intenta con una búsqueda más específica.")
                return []
        except requests.exceptions.RequestException as e:
            st.error(f'Error al consultar la base de datos: {e}')
            return []
    
    return []

# Streamlit app
def main():
    st.title('Buscador bibliográfico')
    st.markdown('''
    Esta aplicación te ayuda a encontrar recursos bibliográficos académicos disponibles públicamente para tu tema de investigación. 
    Busca en bases de datos similares a Google Scholar y muestra citas en formato APA con enlaces a los documentos.
    
    **Consejos de búsqueda:**
    - Usa comillas para frases exactas: `"machine learning"`
    - Puedes combinar frases exactas y palabras sueltas: `"machine learning" deep`
    - Las frases entre comillas se buscarán literalmente
    ''')
    
    query = st.text_input('Introduce el tema o palabras clave de tu investigación:', '')
    num_results = st.slider('Número de resultados a mostrar:', 1, 20, 10)
    
    if st.button('Buscar'):
        if not query.strip():
            st.error('Por favor, ingresa un tema o palabras clave para buscar.')
            return
            
        with st.spinner('Buscando recursos...'):
            results = query_crossref(query, rows=num_results)
            if results:
                st.success(f'Se encontraron {len(results)} resultados relevantes.')
                for idx, res in enumerate(results, 1):
                    st.markdown(f'### {idx}. {res["title"]}')
                    authors = ', '.join(res['authors']) if res['authors'] else 'No disponible'
                    st.markdown(f'**Autores:** {authors}')
                    year = res['year'] if res['year'] else 'No disponible'
                    st.markdown(f'**Año:** {year}')
                    journal = res['journal'] if res['journal'] else 'No disponible'
                    st.markdown(f'**Revista:** {journal}')
                    st.markdown(f'**Cita APA:** {res["citation"]}')
                    if res['url']:
                        st.markdown(f'[Enlace al documento]({res["url"]})')
                    st.markdown('---')
            else:
                st.warning('No se encontraron recursos para la consulta proporcionada.')

if __name__ == '__main__':
    main()
