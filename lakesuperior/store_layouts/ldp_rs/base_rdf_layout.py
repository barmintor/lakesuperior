import logging

from abc import ABCMeta, abstractmethod

from flask import current_app
from rdflib.namespace import RDF
from rdflib.query import ResultException
from rdflib.resource import Resource
from rdflib.term import URIRef

from lakesuperior.dictionaries.namespaces import ns_collection as nsc
from lakesuperior.dictionaries.namespaces import ns_mgr as nsm
from lakesuperior.exceptions import ResourceNotExistsError
from lakesuperior.messaging.messenger import Messenger
from lakesuperior.store_layouts.ldp_rs.graph_store_connector import \
        GraphStoreConnector
from lakesuperior.toolbox import Toolbox



class BaseRdfLayout(metaclass=ABCMeta):
    '''
    This class exposes an interface to build graph store layouts. It also
    provides the baics of the triplestore connection.

    Some store layouts are provided. New ones aimed at specific uses
    and optimizations of the repository may be developed by extending this
    class and implementing all its abstract methods.

    A layout is implemented via application configuration. However, once
    contents are ingested in a repository, changing a layout will most likely
    require a migration.

    The custom layout must be in the lakesuperior.store_layouts.rdf
    package and the class implementing the layout must be called
    `StoreLayout`. The module name is the one defined in the app
    configuration.

    E.g. if the configuration indicates `simple_layout` the application will
    look for
    `lakesuperior.store_layouts.rdf.simple_layout.SimpleLayout`.

    Some method naming conventions:

    - Methods starting with `get_` return a resource.
    - Methods starting with `list_` return an iterable or generator of URIs.
    - Methods starting with `select_` return an iterable or generator with
      table-like data such as from a SELECT statement.
    - Methods starting with `ask_` return a boolean value.
    '''

    # N.B. This is Fuseki-specific.
    UNION_GRAPH_URI = URIRef('urn:x-arq:UnionGraph')

    _logger = logging.getLogger(__name__)


    ## MAGIC METHODS ##

    def __init__(self, config):
        '''Initialize the graph store and a layout.

        NOTE: `rdflib.Dataset` requires a RDF 1.1 compliant store with support
        for Graph Store HTTP protocol
        (https://www.w3.org/TR/sparql11-http-rdf-update/). Blazegraph supports
        this only in the (currently unreleased) 2.2 branch. It works with Jena,
        which is currently the reference implementation.
        '''
        self.config = config
        self._conn = GraphStoreConnector(
                query_ep=config['webroot'] + config['query_ep'],
                update_ep=config['webroot'] + config['update_ep'])


    @property
    def store(self):
        if not hasattr(self, '_store') or not self._store:
            self._store = self._conn.store

        return self._store


    @property
    def ds(self):
        if not hasattr(self, '_ds'):
            self._ds = self._conn.ds
            self._ds.namespace_manager = nsm

        return self._ds


    ## PUBLIC METHODS ##

    #def create_or_replace_rsrc(self, imr):
    #    '''Create a resource graph in the main graph if it does not exist.

    #    If it exists, replace the existing one retaining the creation date.
    #    '''
    #    if self.ask_rsrc_exists(imr.identifier):
    #        self._logger.info(
    #                'Resource {} exists. Removing all outbound triples.'
    #                .format(imr.identifier))
    #        ev_type = self.replace_rsrc(imr)
    #    else:
    #        ev_type = self.create_rsrc(imr)

    #    return ev_type


    #def delete_rsrc(self, urn, inbound=True, delete_children=True):
    #    '''
    #    Delete a resource and optionally its children.

    #    @param urn (rdflib.term.URIRef) URN of the resource to be deleted.
    #    @param inbound (boolean) If specified, delete all inbound relationships
    #    as well (this is the default).
    #    @param delete_children (boolean) Whether to delete all child resources.
    #    This is normally true.
    #    '''
    #    inbound = inbound if self.config['referential_integrity'] == 'none' \
    #            else True
    #    rsrc = self.ds.resource(urn)
    #    children = rsrc[nsc['ldp'].contains * '+'] if delete_children else []

    #    self._do_delete_rsrc(rsrc, inbound)

    #    for child_rsrc in children:
    #        self._do_delete_rsrc(child_rsrc, inbound)
    #        self.leave_tombstone(child_rsrc.identifier, urn)

    #    return self.leave_tombstone(urn)


    ## INTERFACE METHODS ##

    # Implementers of custom layouts should look into these methods to
    # implement.

    @abstractmethod
    def extract_imr(self, uri, strict=False, incl_inbound=False,
                incl_children=True, embed_children=False, incl_srv_mgd=True):
        '''
        Extract an in-memory resource from the dataset restricted to a subject.

        some filtering operations are carried out in this method for
        performance purposes (e.g. `incl_children` and `embed_children`, i.e.
        the IMR will never have those properties). Others, such as
        server-managed triples, are kept in the IMR until they are filtered out
        when the graph is output with `Ldpr.out_graph`.

        @param uri (URIRef) Resource URI.
        @param strict (boolean) If set to True, an empty result graph will
        raise a `ResourceNotExistsError`.
        @param incl_inbound (boolean) Whether to pull triples that have the
        resource URI as their object.
        @param incl_children (boolean) Whether to include all children
        indicated by `ldp:contains`. This is only effective if `incl_srv_mgd`
        is True.
        @param embed_children (boolean) If this and `incl_children` are True,
        the full graph is retrieved for each of the children.
        @param incl_srv_mgd (boolean) Whether to include server-managed
        triples.
        '''
        pass


    @abstractmethod
    def ask_rsrc_exists(self, urn):
        '''
        Ask if a resource is stored in the graph store.

        @param uri (rdflib.term.URIRef) The internal URN of the resource to be
        queried.

        @return boolean
        '''
        pass


    @abstractmethod
    def modify_dataset(self, remove_trp, add_trp):
        '''
        Adds and/or removes triples from the graph.

        This is a crucial point for messaging. Any write operation on the RDF
        store that needs to be notified must be performed by invoking this
        method.

        NOTE: This is not specific to a resource. The LDP layer is responsible
        for checking that all the +/- triples are referring to the intended
        subject(s).

        @param remove_trp (Iterable) Triples to be removed. This can be a graph
        @param add_trp (Iterable) Triples to be added. This can be a graph.
        '''
        pass

