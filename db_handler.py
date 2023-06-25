import sqlalchemy as db
import pandas as pd
from enum import Enum
from datetime import timedelta, datetime
from pretty_html_table import build_table
import human_readable


class JobsDB:
    def __init__(self, generate=False) -> None:
        self.engine = db.create_engine('sqlite:////var/www/api/apiApp/jobs.sqlite', echo=True)
        self.connection = self.engine.connect()
        self.metadata = db.MetaData()
        self.table = db.Table('jobs', self.metadata,
                              db.Column('name', db.String(255), primary_key=True),
                              db.Column('status', db.Enum(self._Status)),
                              db.Column('cluster', db.Enum(self._Cluster)),
                              db.Column('datetime', db.DateTime()),
                              )
        if generate:
            self.generate_table()
        return

    def __enter__(self):
        return self

    def __exit__(self, a, b, c) -> None:
        self.connection.close()
        self.engine.dispose()
        return

    class _Status(Enum):
        submitted = 0
        running = 1
        finished = 2
        failed = 3

        def __str__(self):
            colourDict = {0: 'blue', 1: 'orange', 2: 'teal', 3: 'red'}
            nameDict = {0: 'Submitted', 1: 'Running', 2: 'Finished', 3: 'Failed'}
            return f'<span style="color:{colourDict[self.value]};">{nameDict[self.value]}</span>'

    class _Cluster(Enum):
        monarch = 0
        m3 = 1
        gadi = 2

        def __str__(self):
            colourDict = {0: 'blue', 1: 'green', 2: 'red'}
            nameDict = {0: 'MonARCH', 1: 'M3', 2: 'Gadi'}
            return f'<span style="color:{colourDict[self.value]};">{nameDict[self.value]}</span>'

    def _clusterToEnum(self, cluster: str) -> _Cluster:
        clusterDB = {'monarch': self._Cluster.monarch,
                     'm3': self._Cluster.m3,
                     'gadi': self._Cluster.gadi}
        return clusterDB[cluster.lower()]

    def _statusToEnum(self, status: str) -> _Status:
        statusDB = {'running': self._Status.running,
                    'started': self._Status.running,
                    'submitted': self._Status.submitted,
                    'finished': self._Status.finished,
                    'failed': self._Status.failed}
        return statusDB[status.lower()]

    def generate_table(self) -> None:
        self.metadata.create_all(self.engine)
        return

    def drop_table(self) -> None:
        self.metadata.drop_all(self.engine)
        return

    def add_job(self, name, status, cluster) -> None:
        status_in = self._statusToEnum(status)
        cluster_in = self._clusterToEnum(cluster)
        query = self.table.select().where(self.table.columns.name == name)
        output = self.connection.execute(query)
        fetchone = output.fetchone()
        if fetchone == None:
            update = db.insert(self.table).values(name=name, status=status_in, cluster=cluster_in, datetime=datetime.now())
            self.connection.execute(update)
            self.connection.commit()
            return f'{name} has been added'
        else:
            if status_in == self._Status.finished:
                if datetime.now()-fetchone.datetime < timedelta(seconds=10):
                    return f'{name} has NOT been edited'

            update = db.update(self.table).values({'status': status_in, 'cluster': cluster_in, 'datetime': datetime.now()}).where(self.table.columns.name == name)
            self.connection.execute(update)
            self.connection.commit()
            return f'{name} has been edited'

    def query(self, days: int = 30, search: str = '-') -> str:
        if search == '-':
            query = self.table.select().where(self.table.columns.datetime >= datetime.now()-timedelta(days=days))
        else:
            searchTerms = search.split('+')
            queries = [self.table.select().where(self.table.columns.datetime >= datetime.now()-timedelta(days=days))]
            for subSearch in searchTerms:
                queries += [self.table.select().where(self.table.columns.name.contains(subSearch))]
            query = db.intersect(*queries)

        output = self.connection.execute(query)
        results = output.fetchall()
        df = pd.DataFrame(results)
        try:
            df.columns = self.table.columns.keys()
        except ValueError:
            return "The search returned no results"
        df.sort_values(by='datetime', ascending=False, inplace=True)
        df['datetime'] = df['datetime'].apply(lambda x: human_readable.date_time(datetime.now() - x))
        table = build_table(df[['name', 'status', 'cluster', 'datetime']],
                            'orange_light', text_align='center', escape=False, padding='2px 10px 2px 10px')
        center = '<style>#test {width:100%;height:100%;} table {margin: 0 auto; /* or margin: 0 auto 0 auto */}</style>'
        return center + table
