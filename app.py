import streamlit as st
import requests
from urllib.parse import urlencode
import re

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
    citation = ''
    if authors_str:
        citation += f'{authors_str} '
    if year:
        citation += f'({year}). '
    if title:
        citation += f'{title}. '
    if journal:
        citation += f'{journal}. '
    if doi:
        citation += f'https://doi.org/{doi}'
    elif url:
        citation += url

    return citation.strip()

# Función para consultar la API CrossRef
# CrossRef es una fuente confiable para metadatos de artículos académicos

def query_crossref(query, rows=10):
    base_url = 'https://api.crossref.org/works'
    params = {
        'query.bibliographic': query,
        'rows': rows,
        'filter': 'has-full-text:true'
    }
    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        items = data.get('message', {}).get('items', [])
        results = []
        for item in items:
            title_list = item.get('title', [])
            title = title_list[0] if title_list else ''
            authors = []
            for author in item.get('author', []):
                given = author.get('given', '').strip()
                family = author.get('family', '').strip()
                if given and family:
                    authors.append(f'{given} {family}')
                elif family:
                    authors.append(family)
                elif given:
                    authors.append(given)
            year = None
            if 'published-print' in item and 'date-parts' in item['published-print']:
                year = item['published-print']['date-parts'][0][0]
            elif 'published-online' in item and 'date-parts' in item['published-online']:
                year = item['published-online']['date-parts'][0][0]
            journal = ''
            if 'container-title' in item and item['container-title']:
                journal = item['container-title'][0]
            doi = item.get('DOI', '')
            url = ''
            # Priorizar enlace a PDF si disponible
            link = ''
            if 'link' in item:
                for l in item['link']:
                    if l.get('content-type', '') == 'application/pdf':
                        link = l.get('URL', '')
                        break
                if not link:
                    link = item.get('URL', '')
            else:
                link = item.get('URL', '')

            citation = format_apa_citation(title, authors, year, journal, doi, link)
            results.append({
                'title': title,
                'authors': authors,
                'year': year,
                'journal': journal,
                'doi': doi,
                'url': link,
                'citation': citation
            })
        return results
    except requests.exceptions.RequestException as e:
        st.error(f'Error al consultar la base de datos: {e}')
        return []


# Streamlit app

def main():
    st.title('Buscador bibliográfico')
    st.markdown('''
    Esta aplicación te ayuda a encontrar recursos bibliográficos académicos disponibles públicamente para tu tema de investigación. 
    Busca en bases de datos similares a Google Scholar y muestra citas en formato APA con enlaces a los documentos.
    ''')

    query = st.text_input('Introduce el tema o palabras clave de tu investigación:', '')
    num_results = st.slider('Número de resultados a mostrar:', 1, 20, 10)

    if st.button('Buscar') and query.strip():
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
    elif st.button('Buscar') and not query.strip():
        st.error('Por favor, ingresa un tema o palabras clave para buscar.')

if __name__ == '__main__':
    main()
