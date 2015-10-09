import csv

def unicode_csv_reader(unicode_csv_data, dialect=csv.excel, **kwargs):
    # csv.py doesn't do Unicode; encode temporarily as UTF-8:
    csv_reader = csv.reader(utf_8_encoder(unicode_csv_data),
                            dialect=dialect, **kwargs)
    for row in csv_reader:
        # decode UTF-8 back to Unicode, cell by cell:
        yield [unicode(cell, 'utf-8') for cell in row]

def utf_8_encoder(unicode_csv_data):
    for line in unicode_csv_data:
        yield line.encode('utf-8')

def unicode_dict_csv_reader(unicode_csv_data, dialect=csv.excel, **kwargs):
    mapper = None
    for line in unicode_csv_reader(unicode_csv_data, dialect=dialect, **kwargs):
        if mapper is None:
            mapper = line
            continue
        yield dict(zip(mapper,line))
