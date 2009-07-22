# Copyright (C) 2009 by Eric Talevich (eric.talevich@gmail.com)
# This code is part of the Biopython distribution and governed by its
# license. Please see the LICENSE file that should have been included
# as part of this package.

"""Classes corresponding to phyloXML elements.

"""

import re
import warnings

from Bio import Alphabet
from Bio.Seq import Seq
from Bio.SeqFeature import SeqFeature, FeatureLocation
from Bio.SeqRecord import SeqRecord

import BaseTree


class PhyloXMLWarning(Warning):
    """Warning for non-compliance with the phyloXML specification."""
    pass


def check_str(text, testfunc):
    """Check a string using testfunc, and warn if there's no match."""
    if text is not None and not testfunc(text):
        warnings.warn("String %s doesn't match the given regexp" % text,
                      PhyloXMLWarning)

def trim_str(text, maxlen=40):
    if isinstance(text, basestring) and len(text) > maxlen:
        return text[:maxlen-3] + '...'
    return text


# Tree elements

class PhyloElement(BaseTree.TreeElement):
    """Base class for all PhyloXML objects."""
    def __init__(self, **kwargs):
        """Set all keyword arguments as instance attributes.
        """
        self.__dict__.update(kwargs)

    def __str__(self):
        """Show the class name and an identifying attribute."""
        s = self.__class__.__name__
        if hasattr(self, 'name') and self.name:
            return '%s %s' % (s, trim_str(self.name))
        if hasattr(self, 'value') and self.value:
            return '%s %s' % (s, trim_str(self.value))
        if hasattr(self, 'id') and self.id:
            return '%s %s' % (s, self.id)
        return s

    def __repr__(self):
        """Show this object's constructor with its primitive arguments."""
        s = '%s(%s)' % (self.__class__.__name__,
                           ', '.join('%s=%s'
                                    % (key, repr(trim_str(val, maxlen=60)))
                               for key, val in self.__dict__.iteritems()
                               if val is not None
                               and type(val) in (str, int, float, unicode)))
        return s.encode('utf-8')


class Phyloxml(PhyloElement):
    """Root node of the PhyloXML document.

    Contains an arbitrary number of Phylogeny elements, possibly followed by
    elements from other namespaces.

    Attributes:
        (namespace definitions)

    Children:
        phylogenies []
        other []
    """
    def __init__(self, attributes, phylogenies=None, other=None):
        self.attributes = attributes
        self.phylogenies = phylogenies or []
        self.other = other or []

    def __getitem__(self, index):
        """Get a phylogeny by index or name."""
        if isinstance(index, int) or isinstance(index, slice):
            return self.phylogenies[index]
        if not isinstance(index, basestring):
            raise KeyError, "can't use %s as an index" % type(index)
        for tree in self.phylogenies:
            if tree.name == index:
                return tree
        else:
            raise KeyError, "no phylogeny found with name " + repr(index)

    def __iter__(self):
        """Iterate through the phylogenetic trees in this object."""
        return iter(self.phylogenies)

    def __len__(self):
        """Number of phylogenetic trees in this object."""
        return len(self.phylogenies)


class Other(PhyloElement):
    """Container for non-phyloXML elements in the tree."""
    def __init__(self, tag, namespace=None, attributes=None, value=None,
            children=None):
        self.tag = tag
        self.namespace = namespace
        self.attributes = attributes
        self.value = value
        self.children = children or []

    def __iter__(self):
        """Iterate through the children of this object (if any)."""
        return iter(self.children)


class Phylogeny(PhyloElement, BaseTree.Tree):
    """A phylogenetic tree.

    Attributes:
        rooted
        rerootable
        branch_length_unit
        type

    Children:
        name
        id
        description
        date
        confidences []
        clade
        clade_relations []
        sequence_relations []
        properties []
        other []
    """
    def __init__(self, rooted,
            rerootable=None, branch_length_unit=None, type=None,
            # Child nodes
            name=None, id=None, description=None, date=None, clade=None,
            # Collections
            confidences=None, clade_relations=None, sequence_relations=None,
            properties=None, other=None,
            ):
        assert isinstance(rooted, bool)
        PhyloElement.__init__(self, rerootable=rerootable,
                branch_length_unit=branch_length_unit, type=type,
                rooted=rooted, name=name, id=id, description=description,
                date=date, clade=clade,
                confidences=confidences or [],
                clade_relations=clade_relations or [],
                sequence_relations=sequence_relations or [],
                properties=properties or [],
                other=other or [],
                )

    def find(self, cls=None, **kwargs):
        """Find all sub-nodes matching the given attributes.

        See Clade.find() for details.
        """
        return self.clade.find(cls, **kwargs)

    def to_phyloxml(self, **kwargs):
        """Create a new PhyloXML object containing just this phylogeny."""
        return Phyloxml(kwargs, phylogenies=[self])

    @property
    def confidence(self):
        """Equivalent to self.confidences[0] if there is only 1 value.

        See also: Clade.confidence, Clade.taxonomy
        """
        if len(self.confidences) == 0:
            raise RuntimeError("Phylogeny().confidences is empty")
        if len(self.confidences) > 1:
            raise RuntimeError("more than 1 confidence value available; "
                               "use Phylogeny().confidences")
        return self.confidences[0]


class Clade(PhyloElement, BaseTree.Node):
    """Describes a branch of the current phylogenetic tree.

    Used recursively, describes the topology of a phylogenetic tree.

    The parent branch length of a clade can be described either with the
    'branch_length' element or the 'branch_length' attribute (it is not
    recommended to use both at the same time, though). Usage of the
    'branch_length' attribute allows for a less verbose description.

    Element 'confidence' is used to indicate the support for a clade/parent
    branch.

    Element 'events' is used to describe such events as gene-duplications at the
    root node/parent branch of a clade.

    Element 'width' is the branch width for this clade (including parent
    branch). Both 'color' and 'width' elements apply for the whole clade unless
    overwritten in-sub clades.

    Attributes:
        branch_length
        id_source -- link other elements to a clade (on the xml-level)

    Children:
        name
        branch_length -- equivalent to the attribute
        confidences []
        width
        color
        node_id
        taxonomies []
        sequences []
        events
        binary_characters
        distributions []
        date
        references []
        properties []
        clades [] -- recursive
        other []
    """
    def __init__(self,
            # Attributes
            branch_length=None, id_source=None,
            # Child nodes
            name=None, width=None, color=None, node_id=None, events=None,
            binary_characters=None, date=None,
            # Collections
            confidences=None, taxonomies=None, sequences=None,
            distributions=None, references=None, properties=None, clades=None,
            other=None,
            ):
        PhyloElement.__init__(self, id_source=id_source, name=name,
                branch_length=branch_length, width=width, color=color,
                node_id=node_id, events=events,
                binary_characters=binary_characters, date=date,
                confidences=confidences or [],
                taxonomies=taxonomies or [],
                sequences=sequences or [],
                distributions=distributions or [],
                references=references or [],
                properties=properties or [],
                clades=clades or [],
                other=other or [],
                )

    def find(self, cls=None, **kwargs):
        """Find all sub-nodes matching the given attributes.

        The 'cls' argument specifies the class of the sub-node. Nodes that
        inherit from this type will also match. (The default, Tree.PhyloElement,
        matches any standard phyloXML type.)

        The arbitrary keyword arguments indicate the attribute name of the
        sub-node and the value to match: string, integer or boolean. Strings are
        evaluated as regular expression matches; integers are compared directly
        for equality, and booleans evaluate the attribute's truth value (True or
        False) before comparing. To handle nonzero floats, search with a boolean
        argument, then filter the result manually.

        If no keyword arguments are given, then just the class type is used for
        matching.

        The result is an iterable through all matching objects, by depth-first
        search. (Not necessarily the same order as the elements appear in the
        source file!)

        Example:

        >>> tree = PhyloXML.read('phyloxml_examples.xml').phylogenies[5]
        >>> matches = tree.clade.find(code='OCTVU')
        >>> matches.next()
        Taxonomy(code='OCTVU', scientific_name='Octopus vulgaris')
        """ 
        base_class = PhyloElement
        if cls is None:
            cls = base_class

        def is_matching_node(node):
            if isinstance(node, cls):
                if len(kwargs) == 0:
                    # Without further constraints, accept any matching class
                    return True
                for key, pattern in kwargs.iteritems():
                    if not hasattr(node, key):
                        continue
                    target = getattr(node, key)
                    if (isinstance(pattern, basestring)
                            and isinstance(target, basestring)):
                        if re.match(pattern, target):
                            return True
                    elif isinstance(pattern, bool):
                        if pattern == bool(target):
                            return True
                    elif isinstance(pattern, int):
                        if pattern == target:
                            return True
                    else:
                        raise RuntimeError('invalid argument: ' + str(pattern))
            return False

        def local_find(node):
            singles = []
            lists = []
            for name, subnode in sorted(node.__dict__.iteritems()):
                if subnode is None:
                    continue
                if isinstance(subnode, list):
                    lists.extend(subnode)
                else:
                    singles.append(subnode)
            for item in singles + lists:
                if isinstance(item, base_class):
                    if is_matching_node(item):
                        yield item
                    for result in local_find(item):
                        yield result

        return local_find(self)

    def to_phylogeny(self, **kwargs):
        """Create a new phylogeny containing just this clade."""
        # ENH: preserve some attributes of the parent phylogeny
        return Phylogeny(clade=self, **kwargs)

    # Shortcuts for list attributes that are usually only 1 item
    # XXX should these raise RuntimeError, AttributeError or IndexError?
    @property
    def confidence(self):
        if len(self.confidences) == 0:
            raise RuntimeError("Clade().confidences is empty")
        if len(self.confidences) > 1:
            raise RuntimeError("more than 1 confidence value available; "
                               "use Clade().confidences")
        return self.confidences[0]

    @property
    def taxonomy(self):
        if len(self.taxonomies) == 0:
            raise RuntimeError("Clade().taxonomies is empty")
        if len(self.taxonomies) > 1:
            raise RuntimeError("more than 1 taxonomy value available; "
                               "use Clade().taxonomies")
        return self.taxonomies[0]

    # Sequence-type behavior methods

    def __getitem__(self, index):
        """Get a sub-clade by index (integer or slice)."""
        if isinstance(index, int) or isinstance(index, slice):
            return self.clades[index]
        ref = self
        for idx in index:
            ref = ref.clades[idx]
        return ref

    def __iter__(self):
        """Iterate through the clades (sub-nodes) within this clade."""
        return iter(self.clades)

    def __len__(self):
        """Number of clades directy under this element."""
        return len(self.clades)


# Complex types

class Accession(PhyloElement):
    """Captures the local part in a sequence identifier.

    Example: In 'UniProtKB:P17304', the value of Accession is 'P17304'  and the
    'source' attribute is 'UniProtKB'.
    """
    def __init__(self, value, source):
        self.value = value
        self.source = source


class Annotation(PhyloElement):
    """The annotation of a molecular sequence.

    It is recommended to annotate by using the optional 'ref' attribute (some
    examples of acceptable values for the ref attribute: 'GO:0008270',
    'KEGG:Tetrachloroethene degradation', 'EC:1.1.1.1').

    Attributes:
        ref
        source
        evidence -- describe evidence as free text (e.g. 'experimental')
        type

    Children:
        desc -- free text description
        confidence -- state the type and value of support
        properties [] -- typed and referenced annotations from external resources
        uri
    """
    def __init__(self, 
            # Attributes
            ref=None, source=None, evidence=None, type=None,
            # Child nodes
            desc=None, confidence=None, uri=None,
            # Collection
            properties=None):
        PhyloElement.__init__(self, ref=ref, source=source, evidence=evidence,
                type=type, desc=desc, confidence=confidence, uri=uri,
                properties=properties or [])


class BinaryCharacters(PhyloElement):
    """The names and/or counts of binary characters present, gained, and lost
    at the root of a clade. 
    """
    def __init__(self,
            # Attributes
            type=None, gained_count=None, lost_count=None, present_count=None,
            absent_count=None,
            # Child nodes (flattened into collections)
            gained=None, lost=None, present=None, absent=None):
        PhyloElement.__init__(self,
                type=type, gained_count=gained_count, lost_count=lost_count,
                present_count=present_count, absent_count=absent_count,
                gained=gained or [],
                lost=lost or [],
                present=present or [],
                absent=absent or [])


class BranchColor(PhyloElement):
    """Indicates the color of a clade when rendered graphically.

    The color applies to the whole clade unless overwritten by the color(s) of
    sub-clades.

    Color values should be unsigned bytes, or integers from 0 to 255.
    """
    def __init__(self, red, green, blue):
        assert isinstance(red, int)
        assert isinstance(green, int)
        assert isinstance(blue, int)
        self.red = red
        self.green = green
        self.blue = blue

    def to_rgb(self):
        """Return a 24-bit hexadecimal RGB representation of this color.

        The returned string is suitable for use in HTML/CSS.

        Example:

        >>> bc = BranchColor(12, 200, 100)
        >>> bc.to_rgb()
        '0cc864'
        """
        return hex(self.red * (16**4)
                + self.green * (16**2)
                + self.blue)[2:].zfill(6)


class CladeRelation(PhyloElement):
    """Expresses a typed relationship between two clades.

    For example, this could be used to describe multiple parents of a clade.

    Attributes:
        id_ref_0
        id_ref_1
        distance
        type

    Child:
        confidence
    """
    def __init__(self, type, id_ref_0, id_ref_1,
            distance=None, confidence=None):
        PhyloElement.__init__(self, distance=distance, type=type,
                id_ref_0=id_ref_0, id_ref_1=id_ref_1, confidence=confidence)


class Confidence(PhyloElement):
    """A general purpose confidence element.

    For example, this can be used to express the bootstrap support value of a
    clade (in which case the 'type' attribute is 'bootstrap').
    """
    def __init__(self, value, type):
        self.value = value
        self.type = type


class Date(PhyloElement):
    """A date associated with a clade/node.

    Its value can be numerical by using the 'value' element and/or free text
    with the 'desc' element' (e.g. 'Silurian'). If a numerical value is used, it
    is recommended to employ the 'unit' attribute.

    Attributes:
        unit -- type of numerical value (e.g. 'mya' for 'million years ago')
        range (decimal) -- Margin on the numerical value? (maybe deprecated)
    """
    def __init__(self, value=None, desc=None, unit=None, range=None):
        PhyloElement.__init__(self, value=value, desc=desc, unit=unit,
                range=range)

    def __str__(self):
        """Show the class name and the human-readable date."""
        s = self.__class__.__name__
        if self.unit and self.value is not None:
            return '%s %s %s' % (s, self.value, self.unit)
        if self.desc is not None:
            return '%s %s' % (s, self.desc)
        return s


class Distribution(PhyloElement):
    """Geographic distribution of the items of a clade (species, sequences).

    Intended for phylogeographic applications.

    The location can be described either by free text in the 'desc' element
    and/or by the coordinates of one or more 'Points' (similar to the 'Point'
    element in Google's KML format) or by 'Polygons'.
    """
    def __init__(self, desc=None, points=None, polygons=None):
        PhyloElement.__init__(self, desc=desc,
                points=points or [],
                polygons=polygons or [])


class DomainArchitecture(PhyloElement):
    """Domain architecture of a protein.

    Attribute 'length' is the total length of the protein.
    'domains' is a list of ProteinDomain objects.
    """
    def __init__(self, length=None, domains=None):
        # assert len(domains)
        PhyloElement.__init__(self, length=length, domains=domains)


class Events(PhyloElement):
    """Events at the root node of a clade (e.g. one gene duplication)."""
    ok_type = set(('transfer', 'fusion', 'speciation_or_duplication', 'other',
                    'mixed', 'unassigned'))

    def __init__(self, type=None, duplications=None, speciations=None,
            losses=None, confidence=None):
        check_str(type, self.ok_type.__contains__)
        PhyloElement.__init__(self, type=type, duplications=duplications,
                speciations=speciations, losses=losses, confidence=confidence)

    def iteritems(self):
        return ((k, v) for k, v in self.__dict__.iteritems() if v is not None)

    def iterkeys(self):
        return (k for k, v in self.__dict__.iteritems() if v is not None)

    def itervalues(self):
        return (v for v in self.__dict__.itervalues() if v is not None)

    def items(self):
        return list(self.iteritems())

    def keys(self):
        return list(self.iterkeys())

    def values(self):
        return list(self.itervalues())

    def __len__(self):
        return len(self.values())

    def __getitem__(self, key):
        if not hasattr(self, key):
            raise KeyError(key)
        val = getattr(self, key)
        if val is None:
            raise KeyError("%s has not been set in this object" % repr(key))
        return val

    def __setitem__(self, key, val):
        setattr(self, key, val)

    def __delitem__(self, key):
        setattr(self, key, None)

    def __iter__(self):
        return iter(self.iterkeys())

    def __contains__(self, key):
        return (hasattr(self, key) and getattr(self, key) is not None)


class Id(PhyloElement):
    """A general purpose identifier element.

    Allows to indicate the type (or source) of an identifier. 
    """
    def __init__(self, value, type=None):
        PhyloElement.__init__(self, type=type, value=value)


class Point(PhyloElement):
    """Coordinates of a point, with an optional altitude.

    Used by element 'Distribution'.

    Required attribute 'geodetic_datum' is used to indicate the geodetic datum
    (also called 'map datum'). For example, Google's KML uses 'WGS84'.
    """
    def __init__(self, geodetic_datum, lat, long, alt=None):
        PhyloElement.__init__(self, geodetic_datum=geodetic_datum,
                lat=lat, long=long, alt=alt)


class Polygon(PhyloElement):
    """
    """

class Property(PhyloElement):
    """A typed and referenced property from an external resources.

    The value of a property is its mixed (free text) content. Properties can be
    attached to 'Phylogeny', 'Clade', and 'Annotation'.

    Attributes:
        ref -- reference to an external resource

        unit -- the unit of the property. (optional)

        datatype -- indicates the type of a property and is limited to
            xsd-datatypes (e.g. 'xsd:string', 'xsd:boolean', 'xsd:integer',
            'xsd:decimal', 'xsd:float', 'xsd:double', 'xsd:date', 'xsd:anyURI').

        applies_to -- indicates the item to which a property applies to (e.g.
            'node' for the parent node of a clade, 'parent_branch' for the
            parent branch of a clade).

        id_ref -- allows to attached a property specifically to one element (on
            the xml-level). (optional)

    Example:
        <property datatype="xsd:integer" ref="NOAA:depth" applies_to="clade"
        unit="METRIC:m"> 200 </property> 
    """
    def __init__(self, value, ref, applies_to, datatype,
            unit=None, id_ref=None):
        PhyloElement.__init__(self, unit=unit, id_ref=id_ref, value=value,
                ref=ref, applies_to=applies_to, datatype=datatype)


class ProteinDomain(PhyloElement):
    """Represents an individual domain in a domain architecture.

    Attributes:
        start (non-negative integer)
        end (non-negative integer)
        confidence (float) -- can be used to store (i.e.) E-values.
        id -- name/unique identifier 
    """
    # TODO: confirm that 'start' counts from 1, not 0
    def __init__(self, value, start, end, confidence=None, id=None):
        PhyloElement.__init__(self, value=value, start=start, end=end,
                confidence=confidence, id=id)

    @classmethod
    def from_seqfeature(cls, feat):
        return ProteinDomain(feat.id,
                feat.location.nofuzzy_start,
                feat.location.nofuzzy_end,
                confidence=feat.qualifiers.get('confidence'))

    def to_seqfeature(self):
        feat = SeqFeature(location=FeatureLocation(self.start, self.end),
                          id=self.value)
        if hasattr(self, 'confidence'):
            feat.qualifiers['confidence'] = self.confidence
        return feat


class Reference(PhyloElement):
    """
    """

class Sequence(PhyloElement):
    """A molecular sequence (Protein, DNA, RNA) associated with a node.

    'symbol' is a short (maximal ten characters) symbol of the sequence (e.g.
    'ACTM') whereas 'name' is used for the full name (e.g. 'muscle Actin').

    One intended use for 'id_ref' is to link a sequence to a taxonomy (via the
    taxonomy's 'id_source') in case of multiple sequences and taxonomies per
    node. 

    Attributes:
        type -- type of sequence ('dna', 'rna', or 'aa').
        id_ref
        id_source

    Children:
        symbol
        accession
        name
        location -- location of a sequence on a genome/chromosome.
        mol_seq -- the actual sequence
        uri
        annotations []
        domain_architecture
        other []
    """
    re_symbol = re.compile(r'\S{1,10}')
    re_mol_seq = re.compile(r'[a-zA-Z\.\-\?\*_]+')

    def __init__(self, 
            # Attributes
            type=None, id_ref=None, id_source=None,
            # Child nodes
            symbol=None, accession=None, name=None, location=None, mol_seq=None,
            uri=None, domain_architecture=None,
            # Collections
            annotations=None, other=None,
            ):
        check_str(symbol, self.re_symbol.match)
        check_str(mol_seq, self.re_mol_seq.match)
        PhyloElement.__init__(self, type=type, id_ref=id_ref,
                id_source=id_source, symbol=symbol, accession=accession,
                name=name, location=location, mol_seq=mol_seq, uri=uri,
                domain_architecture=domain_architecture,
                annotations=annotations or [],
                other=other or [],
                )

    @classmethod
    def from_seqrecord(cls, record):
        kwargs = {
                'accession': Accession('', record.id),
                'symbol': record.name,
                'name': record.description,
                'mol_seq': str(record.seq),
                }
        if isinstance(record.seq.alphabet, Alphabet.DNAAlphabet):
            kwargs['type'] = 'dna'
        elif isinstance(record.seq.alphabet, Alphabet.RNAAlphabet):
            kwargs['type'] = 'rna'
        elif isinstance(record.seq.alphabet, Alphabet.ProteinAlphabet):
            kwargs['type'] = 'aa'

        # Unpack record.annotations
        annot_attrib = {}
        annot_conf = None
        annot_prop = None
        annot_uri = None
        for key in ('ref', 'source', 'evidence', 'type'):
            if key in record.annotations:
                annot_attrib[key] = record.annotations[key]
        if 'confidence' in record.annotations:
            # NB: record.annotations['confidence'] = [value, type]
            annot_conf = Confidence(*record.annotations['confidence'])
        if 'properties' in record.annotations:
            # NB: record.annotations['properties'] = {...}
            annot_props = [Property(**prop)
                           for prop in record.annotations['properties']]
        if 'uri' in record.annotations:
            # NB: record.annotations['uri'] = {...}
            annot_uri = Uri(**record.annotations['uri'])
        kwargs['annotations'] = [Annotation(annot_attrib, {
            'desc': record.annotations.get('desc', None),
            'confidence': annot_conf,
            'properties': [annot_prop],
            'uri': annot_uri,
            })]

        # Unpack record.features
        if record.features:
            kwargs['domain_architecture'] = DomainArchitecture(
                    length=len(record.seq),
                    domains=[ProteinDomain.from_seqfeature(feat)
                             for feat in record.features])

        # Not handled:
        # attributes: id_ref, id_source
        # kwargs['location'] = None
        # kwargs['uri'] = None -- redundant here?
        return Sequence(**kwargs)

    def to_seqrecord(self):
        alphabets = {'dna': Alphabet.generic_dna,
                     'rna': Alphabet.generic_rna,
                     'aa': Alphabet.generic_protein}
        seqrec = SeqRecord(
                Seq(self.mol_seq,
                    alphabets.get(self.type, Alphabet.generic_alphabet)),
                id=str(self.accession),
                name=self.symbol,
                description=self.name,
                # dbxrefs=None,
                # features=None,
                )
        # TODO: repack seqrec.annotations
        return seqrec


class SequenceRelation(PhyloElement):
    """Express a typed relationship between two sequences.

    For example, this could be used to describe an orthology (in which case
    attribute 'type' is 'orthology'). 

    Attributes:
        id_ref_0
        id_ref_1
        distance
        type

    Child:
        confidence
    """
    def __init__(self, type, id_ref_0, id_ref_1,
            distance=None, confidence=None):
        PhyloElement.__init__(self, distance=distance, type=type,
                id_ref_0=id_ref_0, id_ref_1=id_ref_1, confidence=confidence)


class Taxonomy(PhyloElement):
    """Describe taxonomic information for a clade.

    Element 'code' is intended to store UniProt/Swiss-Prot style organism codes
    (e.g. 'APLCA' for the California sea hare 'Aplysia californica').

    Element 'id' is used for a unique identifier of a taxon (for example '6500'
    with 'ncbi_taxonomy' as 'type' for the California sea hare).

    Attributes:
        id_source -- link other elements to a taxonomy (on the XML level)

    Children:
        id
        code
        scientific_name
        common_names []
        rank
        uri
        other []
    """
    re_code = re.compile(r'[a-zA-Z0-9_]{2,10}')
    ok_rank = set(('domain', 'kingdom', 'subkingdom', 'branch', 'infrakingdom',
        'superphylum', 'phylum', 'subphylum', 'infraphylum', 'microphylum',
        'superdivision', 'division', 'subdivision', 'infradivision',
        'superclass', 'class', 'subclass', 'infraclass', 'superlegion',
        'legion', 'sublegion', 'infralegion', 'supercohort', 'cohort',
        'subcohort', 'infracohort', 'superorder', 'order', 'suborder',
        'superfamily', 'family', 'subfamily', 'supertribe', 'tribe', 'subtribe',
        'infratribe', 'genus', 'subgenus', 'superspecies', 'species',
        'subspecies', 'variety', 'subvariety', 'form', 'subform', 'cultivar',
        'unknown', 'other'))

    def __init__(self, 
            # Attributes
            id_source=None,
            # Child nodes
            id=None, code=None, scientific_name=None, rank=None, uri=None,
            # Collections
            common_names=None, other=None,
            ):
        check_str(code, self.re_code.match)
        check_str(rank, self.ok_rank.__contains__)
        PhyloElement.__init__(self, id_source=id_source, id=id, code=code,
                scientific_name=scientific_name, rank=rank, uri=uri,
                common_names=common_names or [],
                other=other or [],
                )

    def __str__(self):
        """Show the class name and an identifying attribute."""
        s = self.__class__.__name__
        if self.code is not None:
            return '%s %s' % (s, self.code)
        if self.scientific_name is not None:
            return '%s %s' % (s, self.scientific_name)
        if self.rank is not None:
            return '%s %s' % (s, self.rank)
        if self.id is not None:
            return '%s %s' % (s, self.id)
        return s


class Uri(PhyloElement):
    """A uniform resource identifier.

    In general, this is expected to be an URL (for example, to link to an image
    on a website, in which case the 'type' attribute might be 'image' and 'desc'
    might be 'image of a California sea hare').
    """
    def __init__(self, value, desc=None, type=None):
        PhyloElement.__init__(self, value=value, desc=desc, type=type)


# Simple types

class AppliesTo(PhyloElement):
    pass

class Doi(PhyloElement):
    pass

# class EventType(PhyloElement):
#     pass

# class MolSeq(PhyloElement):
#     pass

class PropertyDataType(PhyloElement):
    pass

# class Rank(PhyloElement):
#     pass

class SequenceRelationType(PhyloElement):
    pass

# class SequenceSymbol(PhyloElement):
#     pass

class SequenceType(PhyloElement):
    pass

# class id_ref(PhyloElement):
#     pass

# class id_source(PhyloElement):
#     pass

# class ref(PhyloElement):
#     pass
