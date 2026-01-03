class Bag(GnrObject):
    """A container object like a dictionary, but ordered.

    Nested elements can be accessed with a path of keys joined with dots"""
    #-------------------- __init__ --------------------------------
    def __init__(self, source=None,**kwargs):
        """ A new bag can be created in various ways:

        * parsing a local file, a remote url or a text string (see fromXml)
        * converting a dictionary into a Bag
        * passing a list or a tuple just like for the builtin dict() command"""
        GnrObject.__init__(self)
        self._nodes = []
        self._backref = False
        self._node = None
        self._parent = None
        self._symbols = None
        self._upd_subscribers = {}
        self._ins_subscribers = {}
        self._del_subscribers = {}
        self._modified = None
        self._rootattributes = None

        self._template_kwargs = kwargs.get("_template_kwargs", {})

        source=source or kwargs
        if source:
            self.fillFrom(source)

    def _get_parent(self):
        return self._parent

    def _set_parent(self, parent):
        if parent is None:
            self._parent = None
        else:
            #self._parent=weakref.ref(parent)
            self._parent = parent

    parent = property(_get_parent, _set_parent)

    def _get_fullpath(self):
        if self.parent != None:
            parentFullPath = self.parent.fullpath
            if parentFullPath:
                return '%s.%s' % (self.parent.fullpath, self.parentNode.label)
            else:
                return self.parentNode.label

    fullpath = property(_get_fullpath)

    def _set_parentNode(self, node):
        if node != None:
            self._parentNode = node
        else:
            self._parentNode = None

    def _get_parentNode(self):
        return getattr(self,'_parentNode', None)

    parentNode = property(_get_parentNode, _set_parentNode)

    def _get_attributes(self):
        return self.parentNode.getAttr() if self.parentNode else dict()

    attributes = property(_get_attributes)

    def _get_rootattributes(self):
        return self._rootattributes

    def _set_rootattributes(self, attrs):
        self._rootattributes = dict(attrs)

    rootattributes = property(_get_rootattributes, _set_rootattributes)

    def _get_modified(self):
        return self._modified

    def _set_modified(self, value):
        if value == None:
            self._modified = None
            self.unsubscribe('modify__', any=True)
        else:
            if self._modified == None:
                self.subscribe('modify__', any=self._setModified)
            self._modified = value

    modified = property(_get_modified, _set_modified)

    def _setModified(self, **kwargs):
        self._modified = True

    #-------------------- __contains__ --------------------------------
    def __contains__(self, what):
        """The "in" operator can be used to test the existence of a key in a
        bag. Also nested keys are allowed. Return ``True`` if the key exists
        in the Bag, ``False`` otherwise

        :param what: the key path to test"""
        if isinstance(what, str):
            return bool(self.getNode(what))
        elif isinstance(what, BagNode):
            return (what in self._nodes)
        else:
            return False

    #-------------------- getItem --------------------------------
    def getItem(self, path, default=None, mode=None):
        """Return the value of the given item if it is in the Bag, else it returns ``None``,
        so that this method never raises a ``KeyError``
        """
        if not path:
            return self
        path = normalizeItemPath(path)
        if isinstance(path, str):
            if '?' in path:
                path, mode = path.split('?')
                if mode == '': mode = 'k'
        obj, label = self._htraverse(path)
        if isinstance(obj, Bag):
            return obj.get(label, default, mode=mode)
        if hasattr(obj, 'get'):
            value = obj.get(label, default)
            return value
        else:
            return default

    __getitem__ = getItem

    def setdefault(self, path, default=None):
        """If *path* is in the Bag, return its value. If not, insert in the *path* the default value
        and return it. Default defaults to ``None``"""
        node = self.getNode(path)
        if not node:
            self[path] = default
        else:
            return node.value

    def sort(self, pars='#k:a'):
        """Sort nodes by label, value or attribute"""
        def safeCmp(a, b):
            if a is None:
                if b is None:
                    return 0
                return -1
            elif b is None:
                return 1
            else:
                return ((a > b) - (a < b))

        if not isinstance(pars, str):
            self._nodes.sort(key=pars)
        else:
            levels = pars.split(',')
            levels.reverse()
            for level in levels:
                if ':' in level:
                    what, mode = level.split(':')
                else:
                    what = level
                    mode = 'a'
                what = what.strip().lower()
                reverse = (not (mode.strip().lower() in ('a', 'asc', '>')))
                if what == '#k':
                    self._nodes.sort(key=lambda a: a.label.lower(), reverse=reverse)
                elif what == '#v':
                    cmp_func = lambda a, b: safeCmp(a.value, b.value)
                    self._nodes.sort(key=cmp_to_key(cmp_func), reverse=reverse)
                elif what.startswith('#a'):
                    attrname = what[3:]
                    cmp_func = lambda a, b: safeCmp(a.getAttr(attrname), b.getAttr(attrname))
                    self._nodes.sort(key=cmp_to_key(cmp_func), reverse=reverse)
                else:
                    cmp_func = lambda a, b: safeCmp(a.value[what], b.value[what])
                    self._nodes.sort(key=cmp_to_key(cmp_func), reverse=reverse)
        return self

    def sum(self, what='#v'):
        """Sum values or attributes"""
        if ',' in what:
            result = []
            wlist = what.split(',')
            for w in wlist:
                result.append(sum([n or 0 for n in self.digest(w)]))
            return result
        else:
            return sum([n or 0 for n in self.digest(what)])

    def summarizeAttributes(self,attrnames=None):
        result = {}
        for n in self:
            if n.value:
                n.attr.update(n.value.summarizeAttributes(attrnames))
            for k in attrnames:
                result[k] = result.get(k,0) + n.attr.get(k,0)
        return result

    def get(self, label, default=None, mode=None):
        """Get value at single level (not hierarchical)"""
        result = None
        currnode = None
        currvalue = None
        attrname = None
        if not label:
            currnode = self.parentNode
            currvalue = self
        elif label == '#^':
            currnode = self.parent.parentNode
        else:
            if '?' in label:
                label, attrname = label.split('?')
            i = self._index(label)
            if i < 0:
                return default
            else:
                currnode = self._nodes[i]
        if currnode:
            if attrname:
                currvalue = currnode.getAttr(attrname)
            else:
                currvalue = currnode.getValue()
        if not mode:
            result = currvalue
        else:
            cmd = mode.lower()
            if not ':' in cmd:
                result = currnode.getAttr(mode)
            else:
                if cmd == 'k:':
                    result = list(currvalue.keys())
                elif cmd.startswith('d:') or cmd.startswith('digest:'):
                    result = currvalue.digest(mode.split(':')[1])
        return result

    def _htraverse(self, pathlist, autocreate=False, returnLastMatch=False):
        """Receive a hierarchical path as a list and execute one step of the path,
        calling itself recursively. If autocreate mode is ``True``, the method creates all
        the not existing nodes of the pathlist. Return the current node's value
        """
        curr = self
        if isinstance(pathlist, str):
            pathlist = gnrstring.smartsplit(pathlist.replace('../', '#^.'), '.')
            pathlist = [x for x in pathlist if x]
            if not pathlist:
                return curr, ''
        else:
            pathlist = list(pathlist)
        label = pathlist.pop(0)
        while label == '#^' and pathlist:
            curr = curr.parent
            label = pathlist.pop(0)
        if not pathlist:
            return curr, label
        i = curr._index(label)
        if i < 0:
            if autocreate:
                if label.startswith('#'):
                    raise BagException('Not existing index in #n syntax')
                i = len(curr._nodes)
                newnode = BagNode(curr, label=label, value=curr.__class__())
                curr._nodes.append(newnode)
                if self.backref:
                    self._onNodeInserted(newnode, i,reason='autocreate')
            elif returnLastMatch:
                return self.parentNode, '.'.join([label] + pathlist)
            else:
                return None, None
        newcurrnode = curr._nodes[i]
        newcurr = newcurrnode.value #maybe a deferred
        isbag = hasattr(newcurr, '_htraverse')
        if autocreate and not isbag:
            newcurr = curr.__class__()
            self._nodes[i].value = newcurr
            isbag = True
        if isbag:
            return newcurr._htraverse(pathlist, autocreate=autocreate, returnLastMatch=returnLastMatch)
        else:
            if returnLastMatch:
                return newcurrnode, '.'.join(pathlist)
            return newcurr, '.'.join(pathlist)

    def __iter__(self):
        return self._nodes.__iter__()

    def __len__(self):
        return len(self._nodes)

    def __call__(self, what=None):
        if not what:
            return list(self.keys())
        return self[what]

    def __str__(self, exploredNodes=None, mode='static,weak'):
        """Return a formatted representation of the bag contents"""
        if not exploredNodes:
            exploredNodes = {}
        outlist = []
        for idx, el in enumerate(self._nodes):
            attr = '<' + ' '.join(["%s='%s'" % attr for attr in list(el.attr.items())]) + '>'
            if attr == '<>': attr = ''
            try:
                value = el.getValue(mode)
            except:
                value = '****  error ****'
            if isinstance(value, Bag):
                el_id = id(el)
                bf = '(*)' if value.backref else ''
                outlist.append(("%s - (%s) %s%s: %s" %
                                (str(idx), value.__class__.__name__, el.label,bf, attr)))
                if el_id in exploredNodes:
                    innerBagStr = 'visited at :%s' % exploredNodes[el_id]
                else:
                    exploredNodes[el_id] = el.label
                    innerBagStr = '\n'.join(["    %s" % (line,)
                                             for line in str(
                            value.__str__(exploredNodes, mode=mode)).split('\n')])
                outlist.append(innerBagStr)
            else:
                currtype = str(type(value)).split(" ")[1][1:][:-2]
                if currtype == 'NoneType': currtype = 'None'
                if '.' in currtype: currtype = currtype.split('.')[-1]
                if not isinstance(value, str):
                    if isinstance(value, bytes):
                        value = value.decode('UTF-8', 'ignore')
                outlist.append(("%s - (%s) %s: %s  %s" % (str(idx), currtype,
                                                          el.label, str(value), attr)))
        return '\n'.join(outlist)

    def asString(self, encoding='UTF-8', mode='weak'):
        """Call the __str__ method, and return an ascii encoded formatted representation of the Bag"""
        return self.__str__(mode=mode).encode(encoding, 'ignore')

    def keys(self):
        """Return a copy of the Bag as a list of keys"""
        return [x.label for x in self._nodes]

    def values(self):
        """Return a copy of the Bag values as a list"""
        return [x.value for x in self._nodes]

    def items(self):
        """Return a copy of the Bag as a list of tuples containing all key,value pairs"""
        return [(x.label, x.value) for x in self._nodes]

    def iteritems(self):
        for x in self._nodes:
            yield (x.label, x.value)

    def iterkeys(self):
        for x in self._nodes:
            yield x.label

    def itervalues(self):
        for x in self._nodes:
            yield x.value

    def digest(self, what=None, condition=None, asColumns=False):
        """It returns a list of ``n`` tuples including keys and/or values and/or attributes"""
        if not what:
            what = '#k,#v,#a'
        if isinstance(what, str):
            if ':' in what:
                where, what = what.split(':')
                obj = self[where]
            else:
                obj = self
            whatsplit = [x.strip() for x in what.split(',')]
        else:
            whatsplit = what
            obj = self
        result = []
        nodes = obj.getNodes(condition)
        for w in whatsplit:
            if w == '#k':
                result.append([x.label for x in nodes])
            elif callable(w):
                result.append([w(x) for x in nodes])
            elif w == '#v':
                result.append([x.value for x in nodes])
            elif w.startswith('#v.'):
                w, path = w.split('.', 1)
                result.append([x.value[path] for x in nodes if hasattr(x.value, 'getItem')])
            elif w == '#__v':
                result.append([x.staticvalue for x in nodes])
            elif w.startswith('#a'):
                attr = None
                if '.' in w:
                    w, attr = w.split('.', 1)
                if w == '#a':
                    result.append([x.getAttr(attr) for x in nodes])
            else:
                result.append([x.value[w] for x in nodes])
        if asColumns:
            return result
        if len(result) == 1:
            return result.pop()
        return list(zip(*result))

    def columns(self, cols, attrMode=False):
        """Digest as columns"""
        if isinstance(cols, str):
            cols = cols.split(',')
        mode = ''
        if attrMode:
            mode = '#a.'
        what = ','.join(['%s%s' % (mode, col) for col in cols])
        return self.digest(what, asColumns=True)

    def has_key(self, path):
        """Return ``True`` if the given item has the key, ``False`` otherwise"""
        return bool(self.getNode(path))

    def getNodes(self, condition=None):
        """Get the actual list of nodes contained in the Bag."""
        if not condition:
            return self._nodes
        else:
            return [n for n in self._nodes if condition(n)]

    nodes = property(getNodes)

    def popNode(self, path,_reason=None):
        """Pop the given node from a Bag at the relative path and returns it"""
        obj, label = self._htraverse(path)
        if obj:
            n = obj._pop(label,_reason=_reason)
            if n:
                return n

    def pop(self, path, dflt=None,_reason=None):
        """Pop the given item from a Bag at the relative path and returns it"""
        result = dflt
        obj, label = self._htraverse(path)
        if obj:
            n = obj._pop(label,_reason=_reason)
            if n:
                result = n.value
        return result

    delItem = pop
    __delitem__ = pop

    def _pop(self, label,_reason=None):
        """Internal pop by label"""
        p = self._index(label)
        if p >= 0:
            node = self._nodes.pop(p)
            if self.backref:
                self._onNodeDeleted(node, p, reason=_reason)
            return node

    def clear(self):
        """Clear the Bag"""
        oldnodes = self._nodes
        self._nodes = []
        if self.backref:
            self._onNodeDeleted(oldnodes, -1)

    def update(self, otherbag, resolved=False,ignoreNone=False):
        """Update the Bag with the ``key/value`` pairs from *otherbag*"""
        if isinstance(otherbag, dict):
            for k, v in list(otherbag.items()):
                self.setItem(k, v)
            return
        for n in otherbag:
            node_resolver = n.resolver
            node_value = None
            if node_resolver is None or resolved:
                node_value = n.value
                node_resolver = None
            if n.label in list(self.keys()):
                currNode = self.getNode(n.label)
                currNode.attr.update(n.attr)
                if node_resolver is not None:
                    currNode.resolver = node_resolver
                if isinstance(node_value, Bag) and  isinstance(currNode.value, Bag):
                    currNode.value.update(node_value,resolved=resolved,ignoreNone=ignoreNone)
                else:
                    if not ignoreNone or node_value is not None:
                        currNode.value = node_value
            else:
                self.setItem(n.label, node_value, n.attr)

    def __eq__(self, other):
        try:
            if isinstance(other, self.__class__):
                return self._nodes == other._nodes
            else:
                return False
        except:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def diff(self,other):
        if self == other:
            return None
        if not isinstance(other, self.__class__):
            return 'Other class is %s, self class is %s' %(other.__class__,self.__class__)
        if len(other)!=len(self):
            return 'Different length'
        result = []
        for k,n in enumerate(self._nodes):
            if n != other._nodes[k]:
                result.append('Node %i label %s difference %s' %(k,n.label,n.diff(other._nodes[k])))
        return '\n'.join(result)

    def merge(self, otherbag, upd_values=True, add_values=True, upd_attr=True, add_attr=True):
        """Allow to merge two bags into one"""
        result = Bag()
        othernodes = dict([(n.getLabel(), n) for n in otherbag._nodes])
        for node in self.nodes:
            k = node.getLabel()
            v = node.getValue()
            attr = dict(node.getAttr())
            if k in othernodes:
                onode = othernodes.pop(k)
                oattr = onode.getAttr()
                if upd_attr and add_attr:
                    attr.update(oattr)
                elif upd_attr:
                    attr = dict([(ak, oattr.get(ak, av)) for ak, av in list(attr.items())])
                elif add_attr:
                    oattr = dict([(ak, av) for ak, av in list(oattr.items()) if not ak in list(attr.keys())])
                    attr.update(oattr)
                ov = onode.getValue()
                if isinstance(v, Bag) and isinstance(ov, Bag):
                    v = v.merge(ov, upd_values=upd_values, add_values=add_values, upd_attr=upd_attr, add_attr=add_attr)
                elif upd_values:
                    v = ov
            result.setItem(k, v, _attributes=attr)
        if add_values:
            for k, n in list(othernodes.items()):
                result.setItem(k, n.getValue(), _attributes=n.getAttr())
        return result

    def copy(self):
        """Return a Bag copy"""
        return copy.copy(self)

    def deepcopy(self):
        """Return a deep Bag copy"""
        result = Bag()
        for node in self:
            value = node.getStaticValue()
            if isinstance(value, Bag):
                value = value.deepcopy()
            result.addItem(node.label, value, dict(node.getAttr()))
        return result

    def getNodeByAttr(self, attr, value, path=None):
        """Return a BagNode with the requested attribute"""
        bags = []
        if path == None: path = []
        for node in self._nodes:
            if node.hasAttr(attr, value):
                path.append(node.label)
                return node
            if isinstance(node._value, Bag): bags.append(node)

        for node in bags:
            nl = [node.label]
            n = node._value.getNodeByAttr(attr, value, path=nl)
            if n:
                path.extend(nl)
                return n

    def getNodeByValue(self,label,value):
        result = None
        for n in self:
            if n.value and n.value[label] == value:
                result = n
                break
        return result

    def getDeepestNode(self, path=None):
        """Return the deepest matching node in the bag and the remaining path"""
        node, tail_path = self._htraverse(path, returnLastMatch=True)
        if hasattr(node, '_htraverse'):
            node = node.getNode(tail_path)
            tail_path = ''
        if node:
            node._tail_list = []
            if tail_path:
                node._tail_list =  gnrstring.smartsplit(tail_path.replace('../', '#^.'), '.')
            return node

    def getNode(self, path=None, asTuple=False, autocreate=False, default=None):
        """Return the BagNode stored at the relative path"""
        if not path:
            return self.parentNode
        if isinstance(path, int):
            return self._nodes[path]
        obj, label = self._htraverse(path, autocreate=autocreate)

        if isinstance(obj, Bag):
            node = obj._getNode(label, autocreate, default)
            if asTuple:
                return (obj, node)
            return node

    def _getNode(self, label, autocreate, default):
        p = self._index(label)
        if p >= 0:
            node = self._nodes[p]
        elif autocreate:
            node = BagNode(self, label=label, value=default)
            i = len(self._nodes)
            self._nodes.append(node)
            node.parentbag = self
            if self.backref:
                self._onNodeInserted(node, i)
        else:
            node = None
        return node

    def setAttr(self, _path=None, _attributes=None, _removeNullAttributes=True, **kwargs):
        """Allow to set, modify or delete attributes into a node at the given path"""
        self.getNode(_path, autocreate=True).setAttr(attr=_attributes, _removeNullAttributes=_removeNullAttributes,
                                                     **kwargs)

    def getAttr(self, path=None, attr=None, default=None):
        """Get the node's attribute at the given path and return it"""
        node = self.getNode(path)
        if node:
            return node.getAttr(label=attr, default=default)
        else:
            return default

    def delAttr(self, path=None, attr=None):
        """Delete an attribute from a node"""
        return self.getNode(path).delAttr(attr)

    def getInheritedAttributes(self):
        """Get inherited attributes from parent chain"""
        if self.parentNode:
            return self.parentNode.getInheritedAttributes()
        else:
            return dict()

    def _pathSplit(self, path):
        """Split a path string at each '.' and return both a list of nodes' labels
        and the first list's element label."""
        if isinstance(path, str):
            escape = "\\."
            if escape in path:
                path = path.replace(escape, chr(1))
                pathList = path.split('.')
                pathList = [x.replace(chr(1), '.') for x in pathList]
            else:
                pathList = path.split('.')
        else:
            pathList = list(path)

        label = pathList.pop(0)
        return label, pathList

    def asDict(self, ascii=False, lower=False):
        """Convert a Bag in a Dictionary and return it (first level only)"""
        result = {}
        for el in self._nodes:
            key = el.label
            if ascii: key = str(key)
            if lower: key = key.lower()
            result[key] = el.value
        return result

    def asDictDeeply(self, ascii=False, lower=False):
        """Convert a Bag in a Dictionary recursively"""
        d = self.asDict(ascii=ascii, lower=lower)
        for k, v in list(d.items()):
            if isinstance(v, Bag):
                d[k] = v.asDictDeeply(ascii=ascii, lower=lower)
        return d

    def appendNode(self,label,value,_attributes=None,_removeNullAttributes=None,**kwargs):
        attr = dict(_attributes or {})
        attr.update(kwargs)
        n = BagNode(self, label=label, value=value,attr=attr,_removeNullAttributes=_removeNullAttributes)
        self._nodes.append(n)
        return n

    def addItem(self, item_path, item_value, _attributes=None, _position=">", _validators=None, **kwargs):
        """Add an item to the current Bag (allows duplicates)"""
        return self.setItem(item_path, item_value, _attributes=_attributes, _position=_position,
                            _duplicate=True, _validators=_validators, **kwargs)

    def setItem(self, item_path, item_value, _attributes=None, _position=None, _duplicate=False,
                _updattr=False, _validators=None, _removeNullAttributes=True,_reason=None, **kwargs):
        """Set an item (values and eventually attributes) to your Bag using a path"""
        if kwargs:
            _attributes = dict(_attributes or {})
            _validators = dict(_validators or {})
            _attributes.update(kwargs)
        if item_path == '' or item_path is True:
            if isinstance(item_value, BagResolver):
                item_value = item_value()
            if isinstance(item_value, Bag):
                for el in item_value:
                    self.setItem(el.label, el.value, _attributes=el.attr, _updattr=_updattr)
                    if el._validators:
                        self.getNode(el.label)._validators = el._validators
            elif 'items' in dir(item_value):
                for key, v in list(item_value.items()): self.setItem(key, v)
            return self
        else:
            item_path = normalizeItemPath(item_path)
            obj, label = self._htraverse(item_path, autocreate=True)
            obj._set(label, item_value, _attributes=_attributes, _position=_position,
                     _duplicate=_duplicate, _updattr=_updattr,
                     _validators=_validators, _removeNullAttributes=_removeNullAttributes,_reason=_reason)

    __setitem__ = setItem

    def _set(self, label, value, _attributes=None, _position=None,
             _duplicate=False, _updattr=False, _validators=None, _removeNullAttributes=True,_reason=None):
        resolver = None
        if isinstance(value, BagResolver):
            resolver = value
            value = None
            if resolver.attributes:
                _attributes = dict(_attributes or ()).update(resolver.attributes)
        i =  -1 if _duplicate else self._index(label)
        if i < 0 :
            if label.startswith('#'):
                raise BagException('Not existing index in #n syntax')
            else:
                bagnode = BagNode(self, label=label, value=value, attr=_attributes,
                                  resolver=resolver, validators=_validators,
                                  _removeNullAttributes=_removeNullAttributes)
                self._insertNode(bagnode, _position,_reason=_reason)
        else:
            node = self._nodes[i]
            if resolver != None:
                node.resolver = resolver
            if _validators:
                node.setValidators(_validators)
            node.setValue(value, _attributes=_attributes, _updattr=_updattr,
                          _removeNullAttributes=_removeNullAttributes,_reason=_reason)

    def getResolver(self, path):
        """Get the resolver of the node at the given path"""
        return self.getNode(path).getResolver()

    def setResolver(self, path, resolver):
        """Set a resolver into the node at the given path"""
        return self.setItem(path, None, resolver=resolver)

    def setBackRef(self, node=None, parent=None):
        """Force a Bag to a more strict structure (tree-leaf model)"""
        if self._backref != True:
            self._backref = True
            self.parent = parent
            self.parentNode = node
            for node in self:
                node.parentbag = self

    def delParentRef(self):
        """Set ``False`` in the ParentBag reference of the relative Bag"""
        self.parent = None
        self._backref = False

    def clearBackRef(self):
        """Clear all the setBackRef() assumption"""
        if self._backref:
            self._backref = False
            self.parent = None
            self.parentNode = None
            for node in self:
                node.parentbag = None
                value = node.staticvalue
                if isinstance(value, Bag):
                    value.clearBackRef()

    def _get_backref (self):
        return self._backref

    backref = property(_get_backref)

    def _insertNode(self, node, position,_reason=None):
        if isinstance(position,int):
            n = position
        elif not (position) or position == '>':
            n = -1
        elif position == '<':
            n = 0
        elif position[0] == '#':
            n = int(position[1:])
        else:
            if position[0] in '<>':
                position, label = position[0], position[1:]
            else:
                position, label = '<', position
            if label[0] == '#':
                n = int(label[1:])
            else:
                n = self._index(label)
            if position == '>' and n >= 0:
                n = n + 1
        if n < 0:
            n = len(self._nodes)
        self._nodes.insert(n, node)
        node.parentbag = self
        if self.backref:
            self._onNodeInserted(node, n,reason=_reason)
        return n

    def _index(self, label):
        """Return the label position into a given Bag (not recursive, current level only)"""
        result = -1
        if label.startswith('#'):
            if '=' in label:
                k, v = label[1:].split('=')
                if not k: k = 'id'
                for idx, el in enumerate(self._nodes):
                    if el.attr.get(k, None) == v:
                        result = idx
                        break
            else:
                idx = int(label[1:])
                if idx < len(self._nodes): result = idx
        else:
            for idx, el in enumerate(self._nodes):
                if el.label == label:
                    result = idx
                    break
        return result

    def _onNodeChanged(self, node, pathlist, evt, oldvalue=None,reason=None):
        """Trigger for node change events"""
        for s in list(self._upd_subscribers.values()):
            s(node=node, pathlist=pathlist, oldvalue=oldvalue, evt=evt,reason=reason)
        if self.parent:
            self.parent._onNodeChanged(node, [self.parentNode.label] + pathlist, evt, oldvalue,reason=reason)

    def _onNodeInserted(self, node, ind, pathlist=None,reason=None):
        """Trigger for node insert events"""
        parent = node.parentbag
        if parent != None and parent.backref and hasattr(node._value, '_htraverse'):
            node._value.setBackRef(node=node, parent=parent)

        if pathlist == None:
            pathlist = []
        for s in list(self._ins_subscribers.values()):
            s(node=node, pathlist=pathlist, ind=ind, evt='ins',reason=reason)
        if self.parent:
            self.parent._onNodeInserted(node, ind, [self.parentNode.label] + pathlist,reason=reason)

    def _onNodeDeleted(self, node, ind, pathlist=None,reason=None):
        """Trigger for node delete events"""
        for s in list(self._del_subscribers.values()):
            s(node=node, pathlist=pathlist, ind=ind, evt='del',reason=reason)
        if self.parent:
            if pathlist == None:
                pathlist = []
            self.parent._onNodeDeleted(node, ind, [self.parentNode.label] + pathlist,reason=reason)

    def _subscribe(self, subscriberId, subscribersdict, callback):
        if not callback is None:
            subscribersdict[subscriberId] = callback

    def subscribe(self, subscriberId, update=None, insert=None, delete=None, any=None):
        """Provide a subscribing of a function to an event"""
        if self.backref == False:
            self.setBackRef()

        self._subscribe(subscriberId, self._upd_subscribers, update or any)
        self._subscribe(subscriberId, self._ins_subscribers, insert or any)
        self._subscribe(subscriberId, self._del_subscribers, delete or any)

    def unsubscribe(self, subscriberId, update=None, insert=None, delete=None, any=None):
        """Delete a subscription of an event"""
        if update or any:
            self._upd_subscribers.pop(subscriberId, None)
        if insert or any:
            self._ins_subscribers.pop(subscriberId, None)
        if delete or any:
            self._del_subscribers.pop(subscriberId, None)

    def setCallBackItem(self, path, callback, **kwargs):
        """An alternative syntax for a BagCbResolver call"""
        resolver = BagCbResolver(callback, **kwargs)
        self.setItem(path, resolver, **kwargs)

    def cbtraverse(self, pathlist, callback, result=None, **kwargs):
        """Walk with callback for each step"""
        if result is None:
            result = []
        if isinstance(pathlist, str):
            pathlist = gnrstring.smartsplit(pathlist.replace('../', '#^.'), '.')
            pathlist = [x for x in pathlist if x]
        label = pathlist.pop(0)
        i = self._index(label)
        if i >= 0:
            result.append(callback(self._nodes[i], **kwargs))
            if pathlist:
                self._nodes[i].getValue().cbtraverse(pathlist, callback, result, **kwargs)
        return result

    def nodesByAttr(self,attr,_mode='static',**kwargs):
        if 'value' in kwargs:
            def f(node,r):
                if node.getAttr(attr) == kwargs['value']:
                    r.append(node)
        else:
            def f(node,r):
                if attr in node.attr:
                    r.append(node)
        r = []
        self.walk(f,r=r,_mode=_mode)
        return r

    def findNodeByAttr(self, attr, value,_mode='static',**kwargs):
        def f(node):
            if node.getAttr(attr) == value:
                return node
        return self.walk(f,_mode=_mode)

    def filter(self, cb, _mode='static', **kwargs):
        """Filter nodes by callback"""
        result=Bag()
        for node in self.nodes:
            value = node.getValue(mode=_mode)
            if value and isinstance(value, Bag):
                value=value.filter(cb,_mode=_mode,**kwargs)
                if value:
                    result.setItem(node.label,value,node.attr)
            elif cb(node):
                result.setItem(node.label,value,node.attr)
        return result

    def isEmpty(self,zeroIsNone=False,blankIsNone=False):
        isEmpty = True
        empties = [None]
        if zeroIsNone:
            empties.append(0)
        if blankIsNone:
            empties.append('')
        for node in self.nodes:
            if any([a not in empties for a in list(node.attr.values())]):
                return False
            if isinstance(node.value,Bag):
                if not node.value.isEmpty():
                    return False
            elif node.value not in empties:
                return False
        return isEmpty

    def walk(self, callback, _mode='static', **kwargs):
        """Calls a function for each node of the Bag"""
        result = None
        for k,node in enumerate(self.nodes):
            result = callback(node, **kwargs)
            if result is None:
                value = node.getValue(mode=_mode)
                if isinstance(value, Bag):
                    kw=dict(kwargs)
                    if '_pathlist' in kwargs:
                        kw['_pathlist'] = kw['_pathlist'] + [node.label]
                    if '_indexlist' in kwargs:
                        kw['_indexlist'] = kw['_indexlist'] + [k]
                    result = value.walk(callback, _mode=_mode, **kw)
            if result:
                return result

    def traverse(self):
        """Generator for depth-first traversal"""
        for node in self.nodes:
            yield node
            value = node.getStaticValue()
            if isinstance(value, Bag):
                for node in value.traverse():
                    yield node
