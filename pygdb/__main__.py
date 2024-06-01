from neo4j import GraphDatabase

from svisitor import SVisitor
from logging_settings import logger

import os
from pathlib import Path
import argparse


class Connector:
    """
    connector to interface with neo4j
    requires neo4j, user with password & database named {db_name}
    """
    uri = 'bolt://localhost:7689'
    # set user password with
    # alter user neo4j set password 'password';
    auth = ('neo4j', 'password')
    db_name = 'pygdb'

    def __init__(self, uri=None, auth=None, db_name=None):
        self.driver = GraphDatabase.driver(
            uri=uri or self.uri,
            auth=auth or self.auth,
        )

        self.db_name = db_name or self.db_name
        self.driver.verify_connectivity()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def clear(args):
    db_name = args.conn.db_name
    exists = False
    # check existence
    records, _, _ = args.conn.driver.execute_query('SHOW DATABASES YIELD name')
    for record in records:
        if record.data().get('name') == db_name:
            exists = True
            print(f'Are you sure you want to erase the database {db_name}? [yes/no]')
            ans = input()

            if ans.lower() not in ['y', 'yes']:
                print('Aborting.')
                return

    if exists:
        args.conn.driver.execute_query(f'DROP DATABASE {db_name}', database_=db_name)
    args.conn.driver.execute_query(f'CREATE DATABASE {db_name}')
    print(f'Database {db_name} {'reset' if exists else 'created'} successfully.')


def add(args):
    pass


def query(args):
    pass


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
        help='username and password for Neo4j server, e.g. "neo4j" "password"'
    )

    subparsers = parser.add_subparsers()

    # subcommands are clear, add, query
    clear_parser = subparsers.add_parser('clear', aliases=['c', 'create'], help='reset contents of the database or create database')

    add_parser = subparsers.add_parser('add', aliases=['a'], help='add new package to database')
    add_parser.add_argument(
        '-u', '--uri',
        type=str,
        default='../test/test_package/',
        help='URI of package'
    )

    add_parser.add_argument(
        '-l', '-logging-level',
        type=int,
        choices=range(5),
        default=3,
        help='logging level (critical=0, debug=4)'
    )

    query_parser = subparsers.add_parser('query', aliases=['q'], help='query the database')
    query_parser.add_argument(
        '-q', '--query-string',
        type=str,
        required=True,
        help='query string'
    )

    query_parser.add_argument(
        '-g', '--graphviz',
        action='store_true',
        help='use graphviz to visualize result'
    )

    add_parser.set_defaults(func=add)
    query_parser.set_defaults(func=query)
    clear_parser.set_defaults(func=clear)

    args = parser.parse_args()
    args.conn = Connector(args.server, args.auth)
    print('Connection to server successful.')
    args.func(args)
