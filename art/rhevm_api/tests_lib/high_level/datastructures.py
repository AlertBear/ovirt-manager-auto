import copy

from art.rhevm_api.data_struct import data_structures


class BaseClass(object):
    def _format_string(self, value, input_name):
        return self.gds_format_string(
            data_structures.quote_xml(value).encode(
                data_structures.ExternalEncoding),
            input_name=input_name)

    def _format_boolean(self, value, input_name):
        return self.gds_format_boolean(
            self.gds_str_lower(str(value)), input_name=input_name)

    def _write_one_member(
            self, member, outfile, level, namespace_, entity_name):
        if self.member_data_items_[member].data_type == 'xs:string':
            format_function = self._format_string
        if self.member_data_items_[member].data_type == 'xs:boolean':
            format_function = self._format_boolean
        if self.__getattribute__(member) is not None:
            data_structures.showIndent(outfile, level)

            outfile.write(
                '<%(ns)s%(ent)s>%(value)s</%(ent)s%(ns)s>\n' % {
                    'ns': namespace_, 'ent': entity_name,
                    'value': format_function(
                        self.__getattribute__(member),
                        entity_name)})

    def exportChildren(
            self, outfile, level, namespace_='', name_='',
            fromsubclass_=False):
        for member_name, member_spec in self.member_data_items_.iteritems():
            if member_spec.data_type in ['xs:string', 'xs:boolean']:
                self._write_one_member(member_name, outfile, level, namespace_,
                                       member_name.rstrip("_"))
            elif member_spec.container:
                for item in self.__getattribute__(member_name):
                    item.export(outfile, level, namespace_, name_=member_name)
            elif self.__getattribute__(member_name) is not None:
                self.__getattribute__(member_name).export(
                    outfile, level, namespace_, name_=member_name)

    def _get_python_format_function(self, member_name):
        value = self.__getattribute__(member_name)
        if self.member_data_items_[member_name].data_type == 'xs:string':
            return data_structures.quote_python(value).encode(
                data_structures.ExternalEncoding)
        if self.member_data_items_[member_name].data_type == 'xs:boolean':
            return str(value)

    def _export_literal_child(self, outfile, level, child_name):
        if self.__getattribute__(child_name) is not None:
            data_structures.showIndent(outfile, level)
            outfile.write('%s=%s,\n' % (
                child_name,
                self._get_python_format_function(self, child_name)))

    def _export_collection(self, outfile, level, member_name):
        data_structures.showIndent(outfile, level)

        outfile.write('%s=[\n' % member_name)
        level += 1
        for item in self.__getattribute__(member_name):
            data_structures.showIndent(outfile, level)
            outfile.write('model_.%s(\n' % member_name)
            item.exportLiteral(outfile, level)
            data_structures.showIndent(outfile, level)
            outfile.write('),\n')
        level -= 1
        data_structures.showIndent(outfile, level)
        outfile.write('],\n')

    def _export_object(self, outfile, level, member_name):
        if self.__getattribute__(member_name) is not None:
            data_structures.showIndent(outfile, level)
            outfile.write('%s=model_.%s(\n' % (member_name, member_name))
            self.__getattribute__(member_name).exportLiteral(outfile, level)
            data_structures.showIndent(outfile, level)
            outfile.write('),\n')

    def exportLiteralChildren(self, outfile, level, name_):
        for member_name, member_spec in self.member_data_items_.iteritems():
            if member_spec.data_type in ['xs:string', 'xs:boolean']:
                self._export_literal_child(outfile, level, member_name)
            elif member_spec.container:
                self._export_collection(outfile, level, member_name)
            else:
                self._export_object(outfile, level, member_name)

    def _build_child(self, child, name, node):
        value = child.text
        if self.member_data_items_[name].data_type == 'xs:string':
            value = self.gds_validate_string(value, node, name)
        elif self.member_data_items_[name].data_type == 'xs:boolean':
            if value in ('true', '1'):
                value = True
            elif value in ('false', '0'):
                value = False
            else:
                data_structures.raise_parse_error(child, 'requires boolean')
            value = self.gds_validate_boolean(value, node, name)
        self.__setattr__(name, value)

    def _build_collection(self, child, name):
        obj_ = data_structures.__dict__(name).factory()
        obj_.build(child)
        self.__getattr__(name).append(obj_)

    def _build_object(self, child, name):
        obj_ = data_structures.__dict__(name).factory()
        obj_.build(child)
        self.__setattr__(name, obj_)

    def buildChildren(self, child_, node, nodeName_, fromsubclass_=False):
        if nodeName_ in ['type', 'float', 'build']:
            nodeName_ = nodeName_ + "_"
        if self.member_data_items_[nodeName_].data_type in [
                'xs:string', 'xs:boolean']:
            self._build_child(child_, nodeName_, node)
        elif self.member_data_items_[nodeName_].container:
            self._build_collection(child_, nodeName_)
        else:
            self._build_object(child_, nodeName_)


# name must be the same, otherwise validator fails
class Storage(data_structures.Storage, BaseClass):
    member_data_items_ = copy.copy(data_structures.Storage.member_data_items_)
    member_data_items_['nfs_timeo'] = data_structures.MemberSpec_(
        'nfs_timeo', 'xs:string', 0)
    member_data_items_['nfs_retrans'] = data_structures.MemberSpec_(
        'nfs_retrans', 'xs:string', 0)

    def _format_string(self, value, input_name):
        return BaseClass._format_string(self, value, input_name)

    def _format_boolean(self, value, input_name):
        return BaseClass._format_boolean(self, value, input_name)

    def _write_one_member(
            self, member, outfile, level, namespace_, entity_name):
        return BaseClass._write_one_member(
            self, member, outfile, level, namespace_, entity_name)

    def exportChildren(
            self, outfile, level, namespace_='', name_='Storage',
            fromsubclass_=False):
        super(data_structures.Storage, self).exportChildren(
            outfile, level, namespace_, name_, True)
        BaseClass.exportChildren(
            self, outfile, level, namespace_, name_, True)

    def _get_python_format_function(self, member_name):
        return BaseClass._get_python_format_function(self, member_name)

    def _export_literal_child(self, outfile, level, child_name):
        BaseClass._export_literal_child(self, outfile, level, child_name)

    def _export_collection(self, outfile, level, member_name):
        BaseClass._export_collection(self, outfile, level, member_name)

    def _export_object(self, outfile, level, member_name):
        BaseClass._export_object(self, outfile, level, member_name)

    def exportLiteralChildren(self, outfile, level, name_):
        super(data_structures.Storage, self).exportLiteralChildren(
            outfile, level, name_)
        BaseClass.exportLiteralChildren(self, outfile, level, name_)

    def _build_child(self, child, name, node):
        BaseClass._build_child(self, child, name, node)

    def _build_collection(self, child, name):
        BaseClass._build_collection(self, child, name)

    def _build_object(self, child, name):
        BaseClass._build_object(self, child, name)

    def buildChildren(self, child_, node, nodeName_, fromsubclass_=False):
        BaseClass.buildChildren(self, child_, node, nodeName_, fromsubclass_)
        super(data_structures.Storage, self).buildChildren(
            child_, node, nodeName_, True)


# name must be the same, otherwise validator fails
class StorageConnection(data_structures.StorageConnection, BaseClass):
    member_data_items_ = copy.copy(
        data_structures.StorageConnection.member_data_items_)
    member_data_items_['port'] = data_structures.MemberSpec_(
        'port', 'xs:string', 0)

    def _format_string(self, value, input_name):
        return BaseClass._format_string(self, value, input_name)

    def _format_boolean(self, value, input_name):
        return BaseClass._format_boolean(self, value, input_name)

    def _write_one_member(
            self, member, outfile, level, namespace_, entity_name):
        return BaseClass._write_one_member(
            self, member, outfile, level, namespace_, entity_name)

    def exportChildren(
            self, outfile, level, namespace_='', name_='Storage',
            fromsubclass_=False):
        super(data_structures.StorageConnection, self).exportChildren(
            outfile, level, namespace_, name_, True)
        BaseClass.exportChildren(
            self, outfile, level, namespace_, name_, True)

    def _get_python_format_function(self, member_name):
        return BaseClass._get_python_format_function(self, member_name)

    def _export_literal_child(self, outfile, level, child_name):
        BaseClass._export_literal_child(self, outfile, level, child_name)

    def _export_collection(self, outfile, level, member_name):
        BaseClass._export_collection(self, outfile, level, member_name)

    def _export_object(self, outfile, level, member_name):
        BaseClass._export_object(self, outfile, level, member_name)

    def exportLiteralChildren(self, outfile, level, name_):
        super(data_structures.StorageConnection, self).exportLiteralChildren(
            outfile, level, name_)
        BaseClass.exportLiteralChildren(self, outfile, level, name_)

    def _build_child(self, child, name, node):
        BaseClass._build_child(self, child, name, node)

    def _build_collection(self, child, name):
        BaseClass._build_collection(self, child, name)

    def _build_object(self, child, name):
        BaseClass._build_object(self, child, name)

    def buildChildren(self, child_, node, nodeName_, fromsubclass_=False):
        BaseClass.buildChildren(self, child_, node, nodeName_, fromsubclass_)
        super(data_structures.StorageConnection, self).buildChildren(
            child_, node, nodeName_, True)
