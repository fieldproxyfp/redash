import cStringIO
import csv
import codecs
import decimal
import datetime
import json
import re
import hashlib
import sqlparse

COMMENTS_REGEX = re.compile("/\*.*?\*/")

def extract_table_names(tokens, tables = set()):
    tokens = [t for t in tokens if t.ttype not in (sqlparse.tokens.Whitespace, sqlparse.tokens.Newline)]
    
    for i in range(len(tokens)):
        if tokens[i].is_group():
            tables.update(extract_table_names(tokens[i].tokens))
        else:
            if tokens[i].ttype == sqlparse.tokens.Keyword \
            and tokens[i].normalized in ['FROM', 'JOIN', 'LEFT JOIN', 'FULL JOIN', 'RIGHT JOIN', 'CROSS JOIN', 'INNER JOIN', 'OUTER JOIN', 'LEFT OUTER JOIN', 'RIGHT OUTER JOIN', 'FULL OUTER JOIN'] \
            and isinstance(tokens[i + 1], sqlparse.sql.Identifier):
                tables.add(tokens[i + 1].value)
    return tables

def gen_query_hash(sql):
    """Returns hash of the given query after stripping all comments, line breaks and multiple
    spaces, and lower casing all text.

    TODO: possible issue - the following queries will get the same id:
        1. SELECT 1 FROM table WHERE column='Value';
        2. SELECT 1 FROM table where column='value';
    """
    sql = COMMENTS_REGEX.sub("", sql)
    sql = "".join(sql.split()).lower()
    return hashlib.md5(sql.encode('utf-8')).hexdigest()


class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoding class, to handle Decimal and datetime.date instances.
    """
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)

        if isinstance(o, datetime.date):
            return o.isoformat()

        super(JSONEncoder, self).default(o)


def json_dumps(data):
    return json.dumps(data, cls=JSONEncoder)


class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """
    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def _encode_utf8(self, val):
        if isinstance(val, (unicode, str)):
            return val.encode('utf-8')

        return val

    def writerow(self, row):
        self.writer.writerow([self._encode_utf8(s) for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)