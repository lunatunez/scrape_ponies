#!/usr/bin/env python
"""
Scraping the pony lists from mlp.wikia.com
Each page has a legend table and a table containing a list of all the ponies and their attributes.

The main table has a class: "wikitable sortable listofponies jquery-tablesorter p402_hide"

With columns:
    Name
    Kind(K)
    Group(G)
    Coat color(C)
    Mane Color(M)
    Eye Color(E)
    First appearance(F) - Season Episode Minute Second
    Description and appearance
    Image
"""
from pprint import pprint
import argparse
import images
import scrapekit

DATA_DIR = './data/'

# URLSLists of all relevant and official characters in the MLP universe.
URLS = {
    'unicorns': 'http://mlp.wikia.com/wiki/List_of_ponies/Unicorn_ponies',
    'pegasus': 'http://mlp.wikia.com/wiki/List_of_ponies/Pegasus_ponies',
    'earthponies': 'http://mlp.wikia.com/wiki/List_of_ponies/Earth_ponies',
    'crystal': 'http://mlp.wikia.com/wiki/List_of_ponies/Crystal_Ponies',
    'elders': 'http://mlp.wikia.com/wiki/List_of_ponies/Elders',
    'foals': 'http://mlp.wikia.com/wiki/List_of_ponies/Foals',
    'mentioned': 'http://mlp.wikia.com/wiki/List_of_ponies/Mentioned_ponies',
    'comic': 'http://mlp.wikia.com/wiki/List_of_comic_ponies',
    'wonderbolts': 'http://mlp.wikia.com/wiki/List_of_Wonderbolts',
    'alicorns': 'http://mlp.wikia.com/wiki/List_of_ponies/Alicorn_ponies',
    'prose': 'http://mlp.wikia.com/wiki/List_of_prose_ponies',
    'other': 'http://mlp.wikia.com/wiki/List_of_non-pony_characters',
}


def remove_unknown(rows):
    return [r for r in rows if 'Unnamed' not in r[0]]


def clean_name(name):
    """
    Cleans up any undesirable noise in the scraped name.
    """
    n = scrapekit.fix_camelcase(name, ':')  # Fix camelCase errors
    n = n.replace('[sic]', '')  # Remove any [sic]'s# Remove any [sic]'s
    # Clean name of '/'
    n = n.replace('/', 'or')
    return n.strip()   # Strip any spaces


def get_rows(urls):
    rows = []
    for url in urls:
        print('Scraping {}'.format(url))
        soup = scrapekit.handle_url(url)
        table = soup.find('table', {'class': 'listofponies'})
        rows.extend(table_to_list(table))
    return rows


def table_to_list(table):
    """ Extracts all the rows in a table and gets the last row as a hyperlink """
    table_rows = table.findAll('tr')
    list_of_rows = []

    # Check the top row for a header
    header = [cell.text.encode('utf-8').strip() for cell in table_rows[0].findAll('th')]
    list_of_rows.append(header)

    for row in table_rows:
        cells = row.findAll('td')
        if cells:
            utf8_row = [cell.text.encode('utf-8') for cell in cells[:-1]]

            # Get the image url - usually in the last column
            a = cells[-1].find('a')
            if a:
                link = a.attrs.get('href', 'None')
                utf8_row.append(link.encode('utf-8'))
            list_of_rows.append(utf8_row)

    return list_of_rows

def process_rows(rows, args):
    """ Clean up table rows that we extracted. """
    # Keep unnamed ponies/characters?
    if args.known:
        rows = remove_unknown(rows)

    # Cleanup names (think about cleaning other rows in the future -
    for r in rows:
        r[0] = clean_name(r[0])

    if args.strip_labels:
        for r in rows:
            r[0] = scrapekit.strip_label(r[0])

    # Check if we only want the names.
    if args.names:
        # note: we have to keep it a list of lists for file processing
        rows = [[r[0]] for r in rows]
    return rows


def write_file(list_of_rows, args):
    """ creates a descriptive filename and writes the file to the appropriate file format. """
    label = 'ponylist'
    components = [label, args.type]
    if args.names:
        components.append('names')
    if args.strip_labels:
        components.append('striplabels')
    if args.known:
        components.append('known')

    filename = scrapekit.DATADIR + '_'.join(components) + '.' + args.format

    print('Writing to {}.'.format(filename))

    if args.format == 'csv':
        scrapekit.write_rows_to_csv(list_of_rows, filename)

    elif args.format == 'txt':
        scrapekit.write_rows_to_txt(list_of_rows, filename)


def make_parser():
    """ Creates the argument parser. """
    parser = argparse.ArgumentParser(
        description='List all ponies, or specific categories of characters, from My Little Pony songs from mlp.wikia.com.')

    type_choices = URLS.keys()
    type_choices.append('all')

    v_group = parser.add_mutually_exclusive_group()
    v_group.add_argument('-v', '--verbose', action='count',
                         help='Display extra details while processing.')
    v_group.add_argument('-q', '--quiet', action='store_true',
                         help="Don't display text while processing.")

    parser.add_argument('type', type=str, choices=type_choices,
                        help='The category of pony to list')
    parser.add_argument('-i', '--images', action='store_true',
                        help='Download all images found on the list(s) and creates a browsable image table in the downloaded image directory. (only download images)')
    parser.add_argument('-n', '--names', action='store_true',
                        help='Only get the pony names, discard all other columns.')

    parser.add_argument('-f', '--format', type=str, choices=['txt', 'csv'],
                        help='Download the info to file format of your choice.')
    parser.add_argument('-s', '--strip-labels', action='store_true',
                        help='Removes any labels from character names\n(ie: Removes "Bright Pony: " from "Bright Pony: Sunshine Smiles"')

    parser.add_argument('-k', '--known', action='store_true',
                        help='Discards any "Unnamed" names from our results.')

    return parser


def main():
    """ Main entry point. """
    parser = make_parser()
    args = parser.parse_args()

    if args.type == 'all':
        if scrapekit.confirm('scrape ALL categories'):
            scraping_urls = URLS.values()
    else:
        # Scrape one category
        scraping_urls = [URLS[args.type]]

    rows = get_rows(scraping_urls)

    original_count = len(rows)
    rows = process_rows(rows=rows, args=args)

    # Filework
    if args.images:
        img_dir = DATA_DIR + 'images_' + args.type + '/'
        images.get_images(rows, img_dir)

        # Create an image sheet
        images.mk_img_sheet(img_dir)
        exit()

    # Info and summary section
    if args.verbose:
        for r in rows:
            pprint(r)

    if not args.quiet:
        sep = '-'*60
        print('')
        print(sep.center(80))
        print('SUMMARY'.center(80))
        print('')
        print('Type selected:      {}'.format(args.type))
        print('Total rows scraped: {}'.format(original_count))
        print('Total rows kept:    {}'.format(len(rows)))
        #  print('Total unique and known names: {}'.format(len(unique_names)))

    if args.format:
        write_file(rows, args)

if __name__ == "__main__":
    main()
