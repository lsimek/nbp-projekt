from neo4j import GraphDatabase, Result
from neo4j.exceptions import ClientError

from svisitor import SVisitor
from snode import SNodeType, SNode
from sgraph import SEdgeType, SEdge, SGraph
from logging_settings import logger

import os
import logging
from pathlib import Path
import argparse
from datetime import datetime


class Connector:
    """
    interface with neo4j
    requires neo4j, user with password & database named {db_name}
    """
    db_name = 'pygdb'
    uri = f'bolt://localhost:7689/'
    # set user password with
    # alter user neo4j set password 'password';
    auth = ('neo4j', 'password')

    def __init__(self, uri=None, auth=None, db_name=None):
        self.driver = GraphDatabase.driver(
            uri=uri or self.uri,
            auth=auth or self.auth,
        )

        self.db_name = db_name or self.db_name
        self.driver.verify_connectivity()
        self.session = self.driver.session(database=self.db_name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()
        self.driver.close()

    @staticmethod
    def create_node_transaction(tx, snode):
        snodetype = snode.snodetype.value
        tx.run(
            f'''
            CREATE (:{snodetype} $snode_attrs)
            ''',
            snode_attrs=vars(snode)
        )

    @staticmethod
    def create_edge_transction(tx, sedge):
        sedgetype= sedge.sedgetype.value
        tx.run(
            f'''
            MATCH (f {{fullname: $first_fullname}}), (s {{fullname: $second_fullname}})
            CREATE (f)-[:{sedgetype} $sedge_attrs]->(s)
            ''',
            first_fullname=sedge.snodes[0].fullname,
            second_fullname=sedge.snodes[1].fullname,
            sedge_type=sedge.sedgetype.value,
            sedge_attrs=vars(sedge)
        )


def clear(args):
    """
    create database or
    reset existing one
    """
    db_name = connector.db_name
    exists = False
    # check existence
    records, _, _ = connector.driver.execute_query('SHOW DATABASES YIELD name')
    for record in records:
        if record.data().get('name') == db_name:
            exists = True
            print(f'Are you sure you want to erase the database {db_name}? [yes/no]')
            ans = input()

            if ans.lower() not in ['y', 'yes']:
                print('Aborting.')
                return

    if exists:
        connector.driver.execute_query(f'DROP DATABASE {db_name}', database_=connector.db_name)

    try:
        connector.driver.execute_query(f'CREATE DATABASE {db_name}', database_=connector.db_name)

        # fullname must be unique
        # this also creates index
        for node_type in [snodetype.value for snodetype in SNodeType]:
            connector.driver.execute_query(
                f'''
                CREATE CONSTRAINT unique_fullname_{node_type} IF NOT EXISTS
                FOR (node: {node_type})
                REQUIRE node.fullname IS UNIQUE
                ''',
                database_=connector.db_name
            )

        # name must exist
        for node_type in [snodetype.value for snodetype in SNodeType]:
            connector.driver.execute_query(
                f'''
                CREATE CONSTRAINT exists_name_{node_type} IF NOT EXISTS
                FOR (node: {node_type})
                REQUIRE node.name IS NOT NULL
                ''',
                database_=connector.db_name
            )

        # create index on name
        node_types = '|'.join([snodetype.value for snodetype in SNodeType])
        connector.driver.execute_query(
            f'''
            CREATE FULLTEXT INDEX fulltextIndexName IF NOT EXISTS
            FOR (node:{node_types})
            ON EACH [node.name]
            ''',
            database_=connector.db_name
        )

        print(f'Database {db_name} {'reset' if exists else 'created'} successfully.')

    except ClientError as e:
        print(f'Database could not be created, error: {e}')


def add(args):
    """
    add new package
    to database
    """
    logging_dict = {
        0: logging.CRITICAL,
        1: logging.ERROR,
        2: logging.WARNING,
        3: logging.INFO,
        4: logging.DEBUG,
    }
    logger.setLevel(logging_dict.get(args.logging_level))

    os.chdir(args.uri)
    sv = SVisitor(root_namespace=args.name)
    sv.scan_package(root_dir=os.getcwd())

    logger.info('Starting transactions.')
    for snode in sv.sgraph.snodes.values():
        connector.session.execute_write(Connector.create_node_transaction, snode)

    logger.info('Nodes done.')
    for sedge in sv.sgraph.sedges:
        connector.session.execute_write(Connector.create_edge_transction, sedge)

    logger.info('Edges done.')
    logger.info('Transactions complete.')


def query(args):
    """
    execute a query and visualize
    with Graphviz
    potentially slow/vulnerable
    """
    os.chdir(Path(__file__).resolve().parent)
    if args.output is None:
        output_folder = '../output/'
        os.makedirs(output_folder, exist_ok=True)
        os.chdir(output_folder)
        output_filename = str(datetime.now()).replace(' ', '_')
    else:
        split_output = args.output.split('/')
        output_filename = split_output[-1]
        if output_filename.endswith('.png'):
            output_filename = output_filename[:-len('.png')]
        output_folder = '/'.join(split_output[:-1])
        if not os.path.exists(output_folder):
            print('The output path does not exist. Create it? [yes/no]')
            ans = input()
            if ans.lower() not in ['yes', 'y']:
                print('Aborting.')
                return

            os.makedirs(output_folder, exist_ok=True)

        os.chdir(output_folder)

    query_graph = connector.driver.execute_query(
        args.query_string,
        database_=connector.db_name,
        result_transformer_=Result.graph
    )

    if result_size := len(query_graph.nodes) > 300:
        raise ValueError(f'Query result too large ({result_size}), will not visualize.')

    sgraph = SGraph()

    for node in query_graph.nodes:
        label = list(node.labels)[0]
        new_snode = SNode(
            snodetype=SNodeType.from_str(label),
            fullname=node.get('fullname'),
            name=node.get('name')
        )

        sgraph.add_snodes(new_snode)

    for edge in query_graph.relationships:
        label = edge.type
        first_snode = sgraph.snodes.get(edge.start_node.get('fullname'))
        second_snode = sgraph.snodes.get(edge.end_node.get('fullname'))
        new_sedge = SEdge(
            (first_snode, second_snode),
            SEdgeType.from_str(label)
        )

        sgraph.add_sedges(new_sedge)

    sgraph.visualize(Path(output_folder) / Path(output_filename), im_format='png')
    print('Done.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='PyGDB CLI')

    parser.add_argument(
        '-s', '--server',
        type=str,
        default=Connector.uri,
        help='URI of Neo4j server, e.g. bolt://localhost:7689'
    )

    parser.add_argument(
        '-a', '--auth',
        type=str,
        default=Connector.auth,
        nargs=2,
        required=False,
        help='username and password for Neo4j server, e.g. "neo4j" "password"'
    )

    parser.add_argument(
        '-d', '--database',
        type=str,
        default=Connector.db_name,
        help='name of database'
    )

    subparsers = parser.add_subparsers()

    # subcommands are clear, add, query
    clear_parser = subparsers.add_parser('clear', aliases=['c', 'create', 'r', 'reset', 'start'], help='reset contents of the database or create database')

    add_parser = subparsers.add_parser('add', aliases=['a'], help='add new package to database')
    add_parser.add_argument(
        '-u', '--uri',
        type=str,
        default='test/',
        help='URI of package'
    )

    add_parser.add_argument(
        '-n', '--name',
        type=str,
        default='root',
        help='name and root namespace of package'
    )

    add_parser.add_argument(
        '-l', '--logging-level',
        type=int,
        choices=range(5),
        default=3,
        help='logging level (critical=0, debug=4)'
    )

    query_parser = subparsers.add_parser('query', aliases=['q'], help='query the database and visualize with graphviz')
    query_parser.add_argument(
        '-q', '--query-string',
        type=str,
        required=True,
        help='query string'
    )

    query_parser.add_argument(
        '-o', '--output',
        type=str,
        required=False,
        help='name of output png file'
    )

    add_parser.set_defaults(func=add)
    query_parser.set_defaults(func=query)
    clear_parser.set_defaults(func=clear)

    args = parser.parse_args()

    with Connector(args.server, args.auth, args.database) as connector:
        print('Connection to server successful.')
        args.func(args)
