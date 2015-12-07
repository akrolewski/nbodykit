from nbodykit.extensionpoints import DataSource
from nbodykit.utils import selectionlanguage
import numpy
import logging
import bigfile

logger = logging.getLogger('BlueTides')

class BlueTidesDataSource(DataSource):
    field_type = "BlueTides"
    @classmethod
    def register(kls):
        
        h = kls.add_parser()
        h.add_argument("path", help="path to file")
        h.add_argument("BoxSize", type=kls.BoxSizeParser,
            help="the size of the isotropic box, or the sizes of the 3 box dimensions")
        h.add_argument("-ptype",
            choices=["0", "1", "2", "3", "4", "5", "FOFGroups"], help="type of particle to read")
        h.add_argument("-weight", choices=['SFR', 'HI'], default=None, 
            help='Weight by sfr or HI, must be with ptype=0')
        h.add_argument("-subsample", action='store_true',
                default=False, help="this is a subsample file")
        h.add_argument("-bunchsize", type=int, default=4 *1024*1024,
                help="number of particle to read in a bunch")
        h.add_argument("-select", default=None, type=selectionlanguage.Query,
            help='row selection e.g. Mass > 1e3 and Mass < 1e5')
    
    def read(self, columns, comm, full=False):
        f = bigfile.BigFile(self.path)
        header = f['header']
        boxsize = header.attrs['BoxSize'][0]

        ptypes = [self.ptype]
        readcolumns = []
        for column in columns:
            if column == 'Weight':
                readcolumns.append('Mass')
                if self.weight == 'HI':
                    readcolumns.append('NeutralHydrogenFraction')
                if self.weight == 'SFR':
                    readcolumns.append('StarFormationRate')
            else:
                readcolumns.append(column)

        for ptype in ptypes:
            for data in self.read_ptype(ptype, readcolumns, comm, full):
                P = dict(zip(readcolumns, data))
                if 'Weight' in columns:
                    if ptype != 'FOFGroups':
                        P['Weight'] = P['Mass']
                        if self.weight == 'HI':
                            P['Weight'] *= P['NeutralHydrogenFraction']
                        if self.weight == 'SFR':
                            P['Weight'] *= P['StarFormationRate']
                    else:
                       P['Weight'] = numpy.ones(len(P['Mass']))

                if 'Position' in columns:
                    P['Position'][:] *= self.BoxSize / boxsize
                    P['Position'][:] %= self.BoxSize

                if 'Velocity' in columns:
                    raise NotImplementedError

                if self.select is not None:
                    mask = self.select.get_mask(P)
                else:
                    mask = Ellipsis
                yield [P[column][mask] for column in columns]

    def read_ptype(self, ptype, columns, comm, full):
        f = bigfile.BigFile(self.path)
        done = False
        i = 0
        while not numpy.all(comm.allgather(done)):
            ret = []
            for column in columns:
                f = bigfile.BigFile(self.path)
                read_column = column
                if self.subsample:
                    if ptype in ("0", "1"):
                        read_column = read_column + '.sample'

                if ptype == 'FOFGroups':
                    if column == 'Position':
                        read_column = 'MassCenterPosition'
                    if column == 'Velocity':
                        read_column = 'MassCenterVelocity'

                cdata = f['%s/%s' % (self.ptype, read_column)]

                Ntot = cdata.size
                start = comm.rank * Ntot // comm.size
                end = (comm.rank + 1) * Ntot //comm.size
                if not full:
                    bunchstart = start + i * self.bunchsize
                    bunchend = start + (i + 1) * self.bunchsize
                    if bunchend > end: bunchend = end
                    if bunchstart > end: bunchstart = end
                else:
                    bunchstart = start
                    bunchend = end
                if bunchend == end:
                    done = True
                data = cdata[bunchstart:bunchend]
                ret.append(data)
            i = i + 1
            yield ret
