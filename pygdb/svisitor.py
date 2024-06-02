from logging_settings import logger
from sgraph import SEdgeType, SEdge, SGraph
from snode import SNodeType, SNode, Dotstring

import ast
import symtable
from collections import deque
from typing import List, Dict, Deque, Tuple, Union, Set
import os
import sys
import tracemalloc
import time
import pathlib
import builtins
from itertools import chain


class SVisitor:
    """
    class that manages SGraph construction
    """
    def __init__(self, root_namespace='root'):
        self.sgraph: SGraph = SGraph()
        self.stack: Deque[Tuple[Dotstring, ast.AST]] = deque()
        self.root_namespace = root_namespace

    def scan_package(self, root_dir: Union[str, pathlib.Path]) -> None:
        tracemalloc.start()
        start_time = time.perf_counter()

        root_path = pathlib.Path(root_dir).resolve()
        os.chdir(root_path)
        logger.info(f'Scanning package at root location {root_path}')

        # path relative to root_path
        def relpath(str_path):
            return pathlib.Path(str_path).resolve().relative_to(root_path)

        root_hasinit = os.path.exists('__init__.py')
        root_snode = SNode(
            fullname=Dotstring(self.root_namespace),
            namespace=Dotstring(self.root_namespace),
            packagename=self.root_namespace,
            snodetype=SNodeType.Package,
            scope_dict={},
            __hasinit__=root_hasinit,
            __imports_from__=[],
            __code__=open('__init__.py').read() if root_hasinit else None,
            __filepath__=pathlib.Path('__init__.py') if os.path.exists('__init__.py') else '.'
        )
        self.add_snodes(root_snode)

        # stack to traverse directories
        stack: Deque[Tuple[SNode, pathlib.Path]] = deque()
        stack.append((root_snode, root_path, ))

        # list of modules to analyze (and package = __init__)
        module_list: Union[List[SNode], Set[SNode]] = [root_snode] if root_snode.attrs.get('__filepath__') != '.' else []

        while stack:
            package_snode, package_path = stack.pop()
            logger.debug(f'Traversing files at {relpath(package_path)}')
            # add folders and .py modules as children to package_snode
            # stop if a folder contains no .py files

            new_dict: Dict[Dotstring, Dotstring] = {}

            for subpath in os.listdir(package_path):
                if os.path.isfile(package_path/subpath) and subpath.endswith('.py') and subpath != '__init__.py':
                    # insert module node to graph and module_list
                    # propagate in scope_dict
                    # add to package's __imports_from__
                    module_name = subpath[:-len('.py')]

                    module_snode = SNode(
                        fullname=package_snode.fullname.concat(module_name),
                        namespace=package_snode.fullname,
                        packagename=package_snode.name,
                        snodetype=SNodeType.Module,
                        scope_dict={},
                        scope_parent=package_snode,
                        __imports_from__=[],
                        __code__=open(package_path/subpath).read(),
                        __filepath__=relpath(package_path/subpath)
                    )

                    logger.debug(f'Adding new module {module_snode.fullname}')
                    self.add_snodes(module_snode)
                    self.add_sedges(SEdge((module_snode, package_snode, ), SEdgeType.WithinScope))

                    module_list.append(module_snode)
                    new_dict[module_snode.fullname] = module_snode.fullname

                    # if package_snode.attrs.get('__code__') is None:
                    package_snode.attrs.get('__imports_from__').append(module_snode)
                    self.add_sedges(SEdge((package_snode, module_snode, ), SEdgeType.ImportsFrom))

                # add package if there are any .py files inside
                elif os.path.isdir(package_path/subpath) and any([filename.endswith('.py') for filename in os.listdir(package_path/subpath)]):
                    # add folder as package if it has any .py files
                    # then also add to stack

                    # check for __init__.py
                    hasinit = os.path.exists(initpath := package_path/subpath/pathlib.Path('__init__.py'))

                    new_package_snode = SNode(
                        fullname=package_snode.fullname.concat(subpath),
                        namespace=package_snode.fullname,
                        packagename=package_snode.fullname,
                        snodetype=SNodeType.Package,
                        scope_dict={},
                        scope_parent=package_snode,
                        __hasinit__=hasinit,
                        __imports_from__=[],
                        __code__=open(initpath).read() if hasinit else None,
                        __filepath__=relpath(initpath) if hasinit else None
                    )

                    logger.debug(f'Adding new package {new_package_snode.fullname}')
                    self.add_snodes(new_package_snode)
                    self.add_sedges(SEdge((new_package_snode, package_snode, ), SEdgeType.WithinScope))

                    module_list.append(new_package_snode) if hasinit else 1
                    new_dict[new_package_snode.fullname] = new_package_snode.fullname

                    # if package_snode.attrs.get('__code__') is None:
                    package_snode.attrs.get('__imports_from__').append(new_package_snode)
                    self.add_sedges(SEdge((package_snode, new_package_snode, ), SEdgeType.ImportsFrom))

                    stack.append((new_package_snode, package_path/subpath))

            self.propagate_scope(package_snode, new_dict)

        logger.info('File traversal finished. Starting first pass.')
        for module_snode in module_list:
            self.first_pass(module_snode)
        logger.info('First passes finished. Starting second pass.')
        for module_snode in module_list:
            self.second_pass(module_snode)
        logger.info('Second passes finished. Setting up plan for third pass.')

        sys.setrecursionlimit(50000)
        # get ordering of modules based on imports
        seen_set = set()
        new_module_list = []

        def rec(snode: SNode):
            if snode in seen_set:
                return
            else:
                seen_set.add(snode)

            for imported_snode in snode.attrs.get('__imports_from__'):
                # if imported_snode.snodetype is SNodeType.Module or imported_snode.attrs.get('__hasinit__'):
                rec(imported_snode)

            if snode.snodetype is SNodeType.Module or snode.attrs.get('__hasinit__') and snode not in new_module_list:
                new_module_list.append(snode)

        rec(root_snode)

        if len(module_list) != len(new_module_list):
        # known to happen from: Python2 scripts, docstring-only modules
            diff = set(module_list) - set(new_module_list) if len(module_list) > len(new_module_list) else set(new_module_list) - set(module_list)
            message = f'Not all modules in list for third pass ({len(module_list)} != {len(new_module_list)})\n{diff=}.'
            # raise Exception(message)
            logger.critical(message)

        module_list = new_module_list
        # module_list = list(set(module_set))

        logger.info(f'Plan set ({len(module_list)} modules). Starting third pass.')
        for module_snode in module_list:
            self.third_pass(module_snode)

        end_time = time.perf_counter()
        logger.info('Finished successfully')
        logger.info(f'Constructed graph with {len(self.sgraph.nodes)} nodes and {len(self.sgraph.edges)} edges.')
        logger.info(f'Used {tracemalloc.get_traced_memory()[1] / 1024**2:.2f} MiB in {end_time - start_time:.2f} seconds.')
        logger.get_stats()

    def first_pass(self, module_snode: SNode) -> None:
        logger.info(f'First pass for {module_snode.fullname}')
        code = module_snode.attrs.get('__code__')
        if code is None:
            logger.debug(f'No code for module/package {module_snode.fullname}')
            return

        table = symtable.symtable(code, module_snode.attrs.get('__filepath__'), compile_type='exec')
        module_name = module_snode.name

        symbol_stack: Deque[Tuple[symtable.SymbolTable, SNode]] = deque()

        # traverse symbol table
        symbol_stack.append((table, module_snode,))
        while symbol_stack:
            top_table, top_snode = symbol_stack.pop()
            logger.debug(f'Checking symbols in namespace {top_snode.fullname}')

            new_dict = {}
            for symbol in top_table.get_symbols():
                if not symbol.is_local() or symbol.is_imported():
                    continue

                new_snode = SNode(
                    fullname=top_snode.fullname.concat(symbol.get_name()),
                    name=symbol.get_name(),
                    namespace=top_snode.fullname,
                    modulename=module_name,
                    packagename=module_snode.packagename,
                    snodetype=SNodeType.Name,
                    scope_dict={},
                    scope_parent=top_snode,
                )

                new_dict[new_snode.fullname] = new_snode.fullname
                self.add_snodes(new_snode)
                self.add_sedges(SEdge(
                    (new_snode, top_snode),
                    SEdgeType.WithinScope
                ))
                logger.debug(f'Added symbol {new_snode.name}')

            # propagate all new names to own scope and parents' scopes
            self.propagate_scope(top_snode, new_dict)

            # add children to stack if Function or Class
            for child in top_table.get_children():
                child_fullname = top_snode.get_local(child.get_name())
                if child_fullname is None:  # unknown error cause?
                    logger.error(f'Child {child_fullname} in {module_snode.fullname} could not be resolved')
                    continue
                child_snode = self.get_snode(child_fullname)
                child_snode.snodetype = SNodeType.Function if child.get_type() == 'function' else SNodeType.Class
                symbol_stack.append((child, child_snode,))
                logger.debug(f'Added to stack {child_snode}')

    def second_pass(self, module_snode: SNode) -> None:
        logger.info(f'Starting second pass for file {module_snode.fullname} (package: {module_snode.packagename})')
        code = module_snode.attrs.get('__code__')
        if code is None:
            logger.debug(f'No code for module/package {module_snode.fullname}')
            return

        tree = ast.parse(code)
        module_snode.add_to_attrs(__ast__=tree)

        fp_stack: Deque[Tuple[Dotstring, ast.AST]] = deque()
        module_snode.ast_node = tree
        fp_stack.append((module_snode.fullname, tree,))

        while fp_stack:
            top_namespace, top_node = fp_stack.pop()

            if isinstance(top_node, ast.Attribute):
                # handle attribute case
                name_list = []
                node = top_node

                while isinstance(node, ast.Attribute):
                    name_list.append(node.attr)
                    node = node.value

                # name_list.append(node.id) if hasattr(node, 'id') else 1  # doesnt need to end with name !?
                if hasattr(node, 'id'):
                    name_list.append(node.id)
                else:
                    continue

                name_list = name_list[::-1]

                if self.get_snode(top_namespace) is None:  # ?
                    logger.error(f'{top_namespace} snode could not be found.')
                    continue

                top_snode = self.resolve_name(self.get_snode(top_namespace), name_list[0])

                logger.debug(f'Attribute chain found: {name_list}')

                if top_snode is None:
                    # name imported with from import
                    continue

                # if name_list[0] == 'self':
                #     # special case - mark as attributes of respective class instead
                #     # top_snode = top_snode.scope_parent
                #     continue

                top_namespace = top_snode.namespace.concat(name_list[0])
                # if this an "attribute" of module or package, do nothing
                if top_namespace not in module_snode.scope_dict:
                    continue

                for name in name_list[1:]:
                    # check if already exists
                    new_fullname = top_namespace.concat(name)
                    new_snode = self.get_snode(new_fullname)

                    # make new snode
                    if new_snode is None:
                        new_snode = SNode(
                            fullname=top_namespace.concat(name),
                            name=top_snode.name.concat(name),
                            namespace=top_namespace,
                            modulename=module_snode.name,
                            packagename=module_snode.packagename,
                            snodetype=SNodeType.Name,
                            scope_dict={},
                            scope_parent=top_snode,
                        )

                        # add to graph
                        self.add_snodes(new_snode)

                        # connect with 'AttributeOf' SEdge
                        new_sedge = SEdge((new_snode, top_snode), SEdgeType.AttributeOf)
                        self.add_sedges(new_sedge)

                        # propagate in scope
                        self.propagate_scope(top_snode, {new_snode.fullname: new_snode.fullname})

                    # set future top_node and top_namespace
                    top_namespace = top_namespace.concat(name)
                    top_snode = new_snode

                # add the list to AST node
                # top_node.name_list = name_list
                top_node.name_dotstring = Dotstring.from_list(name_list)

            # import handling in second pass
            # what about a package wo __init__?
            elif isinstance(top_node, (ast.Import, ast.ImportFrom, )):
                names_list = [name.name for name in top_node.names] if isinstance(top_node, ast.Import) else [top_node.module]

                for name in names_list:
                    if name is None:  # ?
                        logger.error(f'None node detected in module {module_snode.fullname}, {ast.dump(top_node)}')
                        continue
                    if module_snode.snodetype is SNodeType.Module:
                        source_fullname = module_snode.scope_parent.fullname
                    else:
                        source_fullname = module_snode.fullname

                    imported_fullname = source_fullname.concat_rel(name)
                    imported_snode = self.get_snode(imported_fullname)

                    if imported_snode is not None:
                        logger.debug(f'Import detected in second pass: {module_snode} <- {imported_snode}')
                        if imported_snode not in module_snode.attrs.get('__imports_from__'):
                            module_snode.attrs.get('__imports_from__').append(imported_snode)
                            self.add_sedges(SEdge((imported_snode, module_snode, ), SEdgeType.ImportsFrom))

            else:
                new_namespace = top_namespace
                if isinstance(top_node, ast.ClassDef) or isinstance(top_node, ast.FunctionDef):
                    # set new namespace
                    new_namespace = new_namespace.concat(top_node.name)

                # add children
                for child in ast.iter_child_nodes(top_node):
                    fp_stack.append((new_namespace, child))

    def third_pass(self, module_snode: SNode) -> None:
        """
        main AST traversal
        """

        # define handlers and subhandlers
        handlers_dict = {}

        def default_handler():
            """
            add children to stack
            """
            for child in ast.iter_child_nodes(curr_node):
                self.stack.append((top_snode, child, ))

        def import_handler():
            for statement in curr_node.names:
                module_name, alias = statement.name, statement.asname
                if alias is None:
                    alias = module_name

                if module_snode.snodetype is SNodeType.Module:
                    source_fullname = module_snode.scope_parent.fullname
                else:
                    source_fullname = module_snode.fullname

                imported_fullname = source_fullname.concat_rel(module_name)
                imported_snode = self.get_snode(imported_fullname)

                if imported_snode is None:
                    logger.error(f'None node detected in module {top_snode.fullname} with {imported_fullname}')
                    continue

                # add to module's scope dict the imported scope dict, with adequate name changes
                new_dict = {}
                for local_fullname, true_fullname in imported_snode.scope_dict.items():
                    # local_snode = self.get_snode(local_fullname)
                    local_snode = self.get_snode(true_fullname)
                    if local_snode is None:
                        logger.warning(f'{local_snode} could not be imported')
                        continue

                    new_dict[top_snode.fullname.concat(alias).concat(local_snode.name)] = true_fullname

                self.add_sedges(SEdge((imported_snode, top_snode), SEdgeType.ImportedTo, alias=alias))
                top_snode.scope_dict.update(new_dict)
        handlers_dict[ast.Import] = import_handler

        def importfrom_handler():
            module_name = curr_node.module
            if module_name is None:
                logger.error(f'None module in importfrom, {curr_node=}')
                return

            if module_snode.snodetype is SNodeType.Module:
                source_fullname = module_snode.scope_parent.fullname
            else:
                source_fullname = module_snode.fullname

            imported_fullname = source_fullname.concat_rel(module_name)
            imported_snode = self.get_snode(imported_fullname)

            if imported_snode is None:
                logger.error(f'None node detected in module {top_snode.fullname} with {imported_fullname}')
                return

            # add to scope dict
            new_dict = {}
            for statement in curr_node.names:
                source_name, alias = statement.name, statement.asname
                if alias is None:
                    alias = source_name
                if source_name == '*':
                    # implementation for
                    # from ... import *
                    for local_fullname, true_fullname in imported_snode.scope_dict.items():
                        # local_snode = self.get_snode(local_fullname)
                        local_snode = self.get_snode(true_fullname)
                        if local_snode is None:
                            logger.warning(f'{local_snode} could not be imported')
                            continue

                        new_dict[top_snode.fullname.concat(local_snode.name)] = true_fullname
                else:
                    true_fullname = imported_snode.scope_dict.get(imported_snode.fullname.concat(source_name))
                    if true_fullname is None:
                        logger.warning(f'{imported_snode.fullname.concat(source_name)} could not be found in scope of {imported_snode}')
                        continue
                    new_dict[top_snode.fullname.concat(alias)] = true_fullname
                    self.add_sedges(SEdge((self.get_snode(true_fullname), top_snode, ), SEdgeType.ImportedTo, alias=alias))
            top_snode.scope_dict.update(new_dict)
        handlers_dict[ast.ImportFrom] = importfrom_handler

        def classdef_handler():
            class_snode = self.get_snode(top_snode.fullname.concat(curr_node.name))
            class_snode.add_to_attrs(docstring=ast.get_docstring(curr_node))

            for decorator in curr_node.decorator_list:
                decorator_name = resolve_attrs_subhandler(decorator)
                decorator_snode = self.resolve_name(top_snode, decorator_name)
                if decorator_snode is not None:
                    self.add_sedges(SEdge((decorator_snode, class_snode, ), SEdgeType.Decorates))

            for base in curr_node.bases:
                base_name = resolve_attrs_subhandler(base)
                base_snode = self.resolve_name(top_snode, base_name)
                if base_snode is not None:
                    self.add_sedges(SEdge((class_snode, base_snode, ), SEdgeType.InheritsFrom))

            add_body_subhandler(class_snode)
        handlers_dict[ast.ClassDef] = classdef_handler

        def functiondef_handler():
            func_snode = self.get_snode(top_snode.fullname.concat(curr_node.name))
            func_snode.add_to_attrs(docstring=ast.get_docstring(curr_node))

            if isinstance(curr_node, ast.AsyncFunctionDef):
                func_snode.add_to_attrs(isAsync=True)

            for decorator in curr_node.decorator_list:
                decorator_name = resolve_attrs_subhandler(decorator)
                decorator_snode = self.resolve_name(top_snode, decorator_name)
                if decorator_snode is not None:
                    self.add_sedges(SEdge((decorator_snode, func_snode, ), SEdgeType.Decorates))

            # handle return type
            type_node = curr_node.returns
            typing_subhandler(func_snode, type_node)

            # handle args
            arguments = curr_node.args
            args = arguments.posonlyargs + arguments.args + arguments.kwonlyargs
            if arguments.kwarg is not None:
                args += [arguments.kwarg]
            if arguments.vararg is not None:
                args += [arguments.vararg]

            for arg in args:
                arg_snode = self.get_snode(func_snode.fullname.concat(arg.arg))
                self.add_sedges(SEdge((arg_snode, func_snode), SEdgeType.Argument))

                typing_subhandler(arg_snode, arg.annotation)

            # mark as method if needed
            if func_snode.scope_parent.snodetype is SNodeType.Class:
                self.add_sedges(SEdge((func_snode, func_snode.scope_parent), SEdgeType.Method))

            add_body_subhandler(func_snode)
        handlers_dict[ast.FunctionDef] = functiondef_handler
        handlers_dict[ast.AsyncFunctionDef] = functiondef_handler

        def assign_handler():
            targets, value = curr_node.targets, curr_node.value

            for target in targets:
                if isinstance(target, ast.Tuple) and isinstance(value, (ast.Tuple, ast.List)):
                    # try to unpack
                    target = target.elts
                    value = value.elts
                    for _target, _value in zip(target, value):
                        target_name = resolve_attrs_subhandler(_target)
                        target_snode = self.resolve_name(top_snode, target_name)

                        if target_snode is None:
                            continue

                        self.add_sedges(SEdge((target_snode, top_snode), SEdgeType.AssignedToWithin))

                        source_snodes = get_all_names_subhandler(_value)
                        for source_snode in source_snodes:
                            self.add_sedges(SEdge((source_snode, target_snode), SEdgeType.AssignedTo))
                elif isinstance(target, (ast.Attribute, ast.Name)):
                    target_name = resolve_attrs_subhandler(target)
                    target_snode = self.resolve_name(top_snode, target_name)

                    if target_snode is None:
                        continue

                    self.add_sedges(SEdge((target_snode, top_snode), SEdgeType.AssignedToWithin))

                    source_snodes = get_all_names_subhandler(value)

                    for source_snode in source_snodes:
                        self.add_sedges(SEdge((source_snode, target_snode), SEdgeType.AssignedTo))
        handlers_dict[ast.Assign] = assign_handler

        def annassign_handler():
            target, value, annot = curr_node.target, curr_node.value, curr_node.annotation

            target_name = resolve_attrs_subhandler(target)
            target_snode = self.resolve_name(top_snode, target_name)

            if target_snode is None:
                return

            typing_subhandler(target_snode, annot)
            source_snodes = get_all_names_subhandler(value)
            for source_snode in source_snodes:
                self.add_sedges(SEdge((source_snode, target_snode), SEdgeType.AssignedTo))
        handlers_dict[ast.AnnAssign] = annassign_handler

        def namedexpr_handler():
            target, value = curr_node.target, curr_node.value

            target_name = resolve_attrs_subhandler(target)
            target_snode = self.resolve_name(top_snode, target_name)

            if target_snode is None:
                return

            source_snodes = get_all_names_subhandler(value)
            for source_snode in source_snodes:
                self.add_sedges(SEdge((source_snode, target_snode), SEdgeType.AssignedTo))
        handlers_dict[ast.NamedExpr] = namedexpr_handler

        def call_handler():
            """
            here we can find names passed as arg
            to given function
            or class constructor
            """
            pass
        handlers_dict[ast.Call] = call_handler

        def return_handler():
            value = curr_node.value

            source_snodes = get_all_names_subhandler(value)
            for source_snode in source_snodes:
                self.add_sedges(SEdge((source_snode, top_snode), SEdgeType.Returns))
            pass
        handlers_dict[ast.Return] = return_handler

        # subhandlers
        def add_body_subhandler(new_snode: SNode) -> None:
            for child in curr_node.body:
                self.stack.append((new_snode, child, ))

        add_children_subhandler = default_handler

        def resolve_attrs_subhandler(top_node: ast.Name | ast.Attribute) -> Dotstring | None:
            if hasattr(curr_node, 'name_dotstring'):
                # already analyzed
                return curr_node.name_dotstring

            name_list = []
            node = top_node

            while isinstance(node, ast.Attribute):
                name_list.append(node.attr)
                node = node.value

            if hasattr(node, 'id'):
                name_list.append(node.id)
            else:
                return None

            name_list = name_list[::-1]

            # if self.get_snode(top_snode.fullname) is None:  # ?
            #     logger.error(f'{top_snode.fullname} snode could not be found.')
            #     return None

            referenced_snode = self.resolve_name(top_snode, name_list[0])

            if referenced_snode is None:
                # imported name
                return None

            # if name_list[0] == 'self':
            #     # special case
            #     # top_snode = top_snode.scope_parent
            #     return None

            # for imported names, add new attributes defined outside
            # don't do this if the top name is a module/package
            # if referenced_snode.snodetype not in [SNodeType.Module, SNodeType.Package]:
            attr_names = Dotstring('')
            for name in name_list[1:]:
                # check if already exists
                # new_fullname = referenced_snode.fullname.concat(name)
                # new_snode = self.get_snode(new_fullname)
                attr_names = attr_names.concat(name)
                new_snode = self.resolve_name(referenced_snode, attr_names)

                # make new snode
                if new_snode is None:
                    new_snode = SNode(
                        fullname=referenced_snode.fullname.concat(name),
                        name=referenced_snode.name.concat(name),
                        namespace=referenced_snode.fullname,
                        modulename=module_snode.name,
                        packagename=module_snode.packagename,
                        snodetype=SNodeType.Name,
                        scope_dict={},
                        scope_parent=referenced_snode,
                    )

                    # add to graph
                    self.add_snodes(new_snode)

                    # connect with 'AttributeOf' SEdge
                    new_sedge = SEdge((new_snode, referenced_snode), SEdgeType.AttributeOf)
                    self.add_sedges(new_sedge)

                    # propagate in scope
                    self.propagate_scope(referenced_snode, {new_snode.fullname: new_snode.fullname})

                # set future top_node and top_namespace
                referenced_snode = new_snode

            # add RefersToWithinEdge to top_snode
            # this has code duplication, consider making the subhandler return SNode | None instead
            name = Dotstring.from_list(name_list)
            snode = self.resolve_name(top_snode, name)
            self.add_sedges(SEdge((snode, top_snode), SEdgeType.ReferencedWithin))

            return name

        def typing_subhandler(typed_snode, top_node) -> None:
            if top_node is None:
                return
            if isinstance(top_node, ast.Name) and top_node.id in dir(builtins):
                typed_snode.add_to_attrs(type=top_node.id)
            else:
                type_name = resolve_attrs_subhandler(top_node)
                type_snode = self.resolve_name(top_snode, type_name)
                if type_name is not None and type_snode is not None:
                    self.add_sedges(SEdge((typed_snode, type_snode), SEdgeType.TypedWith))

        def get_all_names_subhandler(top_node) -> List[SNode]:
            """
            within a subtree, get all
            mentioned names as snodes
            """
            li: List[SNode] = []

            substack = deque()
            substack.append(top_node)

            while substack:
                subcurr_node = substack.pop()
                for child in chain(ast.iter_child_nodes(subcurr_node), [subcurr_node]):
                    if isinstance(child, (ast.Attribute, ast.Name)):
                        new_ds = resolve_attrs_subhandler(child)
                        new_snode = self.resolve_name(top_snode, new_ds)
                        if new_snode is not None:
                            li.append(new_snode)
                    elif child is not subcurr_node:
                        substack.append(child)
            return li
        # end

        # AST traversal
        logger.info(f'Starting third pass for file {module_snode.fullname} (package: {module_snode.packagename})')
        tree = module_snode.attrs.get('__ast__')  # AST saved in second pass
        module_snode.add_to_attrs(docstring=ast.get_docstring(tree))
        self.stack = deque()
        self.stack.append((module_snode, tree, ))

        while self.stack:
            top_snode, curr_node = self.stack.popleft()
            handler = handlers_dict.get(curr_node.__class__, default_handler)
            # logger.debug(f'handler: {handler.__name__}')
            handler()

    def add_snodes(self, *nodes) -> None:
        self.sgraph.add_nodes(*nodes)

    def add_sedges(self, *edges) -> None:
        self.sgraph.add_edges(*edges)

    def get_snode(self, fullname) -> SNode:
        """
        for given fullname, get unique
        SNode it refers to
        """
        return self.sgraph.nodes.get(fullname, None)

    def resolve_name(self, current_snode: SNode, name: str | Dotstring, allow_none: bool = True) -> SNode | None:
        """
        for given scope and name, get unique
        SNode it refers to
        """
        if isinstance(name, Dotstring):
            name, suffix = name.first, name.wo_first
        else:
            suffix = ''

        fullname = current_snode.fullname.concat(name)
        while fullname not in current_snode.scope_dict and current_snode.scope_parent.scope_parent is not None:
            current_snode = current_snode.scope_parent
            fullname = current_snode.fullname.concat(name)
        fullname = current_snode.scope_dict.get(fullname)

        if fullname is not None:
            return self.get_snode(fullname.concat(suffix))
        elif allow_none:
            return None
        else:
            raise KeyError(f'{name=} in {current_snode} could not be resolved.')

    def propagate_scope(self, current_snode, new_dict: Dict) -> None:
        """
        propagate elements of scope
        to successive parents
        """
        while current_snode is not None:
            current_snode.scope_dict.update(new_dict)
            current_snode = current_snode.scope_parent
