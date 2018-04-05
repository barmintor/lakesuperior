import pdb
import pytest

from io import BytesIO
from uuid import uuid4

from rdflib import Graph, Literal, URIRef

from lakesuperior.api import resource as rsrc_api
from lakesuperior.dictionaries.namespaces import ns_collection as nsc
from lakesuperior.exceptions import (
        InvalidResourceError, ResourceNotExistsError, TombstoneError)
from lakesuperior.globals import RES_CREATED, RES_UPDATED
from lakesuperior.model.ldpr import Ldpr


@pytest.fixture(scope='module')
def random_uuid():
    return str(uuid.uuid4())


@pytest.mark.usefixtures('db')
class TestResourceApi:
    '''
    Test interaction with the Resource API.
    '''
    def test_nodes_exist(self):
        """
        Verify whether nodes exist or not.
        """
        assert rsrc_api.exists('/') is True
        assert rsrc_api.exists('/{}'.format(uuid4())) is False


    def test_get_root_node_metadata(self):
        """
        Get the root node metadata.

        The ``dcterms:title`` property should NOT be included.
        """
        gr = rsrc_api.get_metadata('/')
        assert isinstance(gr, Graph)
        assert len(gr) == 9
        assert gr[gr.identifier : nsc['rdf'].type : nsc['ldp'].Resource ]
        assert not gr[gr.identifier : nsc['dcterms'].title : "Repository Root"]


    def test_get_root_node(self):
        """
        Get the root node.

        The ``dcterms:title`` property should be included.
        """
        rsrc = rsrc_api.get('/')
        assert isinstance(rsrc, Ldpr)
        gr = rsrc.imr
        assert len(gr) == 10
        assert gr[gr.identifier : nsc['rdf'].type : nsc['ldp'].Resource ]
        assert gr[
            gr.identifier : nsc['dcterms'].title : Literal('Repository Root')]


    def test_get_nonexisting_node(self):
        """
        Get a non-existing node.
        """
        with pytest.raises(ResourceNotExistsError):
            gr = rsrc_api.get('/{}'.format(uuid4()))


    def test_create_from_graph(self):
        """
        Create a resource from a provided graph.
        """
        uid = '/rsrc_from_graph'
        uri = nsc['fcres'][uid]
        gr = Graph().parse(
            data='<> a <http://ex.org/type#A> .', format='turtle',
            publicID=uri)
        #pdb.set_trace()
        evt = rsrc_api.create_or_replace(uid, init_gr=gr)

        rsrc = rsrc_api.get(uid)
        assert rsrc.imr[
                rsrc.uri : nsc['rdf'].type : URIRef('http://ex.org/type#A')]
        assert rsrc.imr[
                rsrc.uri : nsc['rdf'].type : nsc['ldp'].RDFSource]


    def test_create_from_rdf_stream(self):
        """
        Create a resource from a RDF stream (Turtle).

        This is the same method used by the LDP endpoint.
        """
        uid = '/rsrc_from_stream'
        uri = nsc['fcres'][uid]
        stream = BytesIO(b'<> a <http://ex.org/type#B> .')
        #pdb.set_trace()
        evt = rsrc_api.create_or_replace(
            uid, stream=stream, mimetype='text/turtle')

        rsrc = rsrc_api.get(uid)
        assert rsrc.imr[
                rsrc.uri : nsc['rdf'].type : URIRef('http://ex.org/type#B')]
        assert rsrc.imr[
                rsrc.uri : nsc['rdf'].type : nsc['ldp'].RDFSource]


    def test_replace_rsrc(self):
        uid = '/test_replace'
        uri = nsc['fcres'][uid]
        gr1 = Graph().parse(
            data='<> a <http://ex.org/type#A> .', format='turtle',
            publicID=uri)
        evt = rsrc_api.create_or_replace(uid, init_gr=gr1)
        assert evt == RES_CREATED

        rsrc = rsrc_api.get(uid)
        assert rsrc.imr[
                rsrc.uri : nsc['rdf'].type : URIRef('http://ex.org/type#A')]
        assert rsrc.imr[
                rsrc.uri : nsc['rdf'].type : nsc['ldp'].RDFSource]

        gr2 = Graph().parse(
            data='<> a <http://ex.org/type#B> .', format='turtle',
            publicID=uri)
        #pdb.set_trace()
        evt = rsrc_api.create_or_replace(uid, init_gr=gr2)
        assert evt == RES_UPDATED

        rsrc = rsrc_api.get(uid)
        assert not rsrc.imr[
                rsrc.uri : nsc['rdf'].type : URIRef('http://ex.org/type#A')]
        assert rsrc.imr[
                rsrc.uri : nsc['rdf'].type : URIRef('http://ex.org/type#B')]
        assert rsrc.imr[
                rsrc.uri : nsc['rdf'].type : nsc['ldp'].RDFSource]
