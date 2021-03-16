from rest_framework import serializers
from nssmf.models import SliceTemplate, GenericTemplate, ServiceMappingPluginModel, Content
from nssmf.enums import OperationStatus, PluginOperationStatus
from free5gmano import settings
import zipfile
import yaml
import os

#通用切片內容
class ContentSerializer(serializers.ModelSerializer): #通用切片內容序列器
    class Meta:
        model = Content #指定序列器所用的Model
        fields = ['contentId', 'type', 'tosca_definitions_version', 'topology_template'] #指定此序列器包含的欄位

#創建、上傳通用樣板
class GenericTemplateSerializer(serializers.ModelSerializer): #通用切片序列器
    content = ContentSerializer(many=True, read_only=True, source='content_set')

    class Meta:
        model = GenericTemplate #指定序列器所用的Model
        fields = ['templateId', 'name', 'nfvoType', 'templateType', 'templateFile', 'content',
                  'operationStatus', 'operationTime', 'description'] #指定此序列器包含的欄位
        read_only_fields = ['templateFile'] #指定此序列器唯讀時包含的欄位

    def create(self, validated_data): #創建通用樣板
        print(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data): #上傳通用樣板
        validated_data['operationStatus'] = OperationStatus.UPDATED
        print(validated_data)
        return super().update(instance, validated_data)

#通用樣板檔案資訊
class GenericTemplateFileSerializer(serializers.ModelSerializer): #上傳通用樣板

    class Meta:
        model = GenericTemplate #指定序列器所用的Model
        fields = ['templateId', 'templateFile', 'templateType', 'operationStatus', 'operationTime'] #指定此序列器唯讀時包含的欄位

    def update(self, instance, validated_data): #檢查是否能上傳
        # if not self.instance.templateType:
        #     raise serializers.ValidationError('This templateType field must be value.')
        validated_data['operationStatus'] = OperationStatus.UPLOAD
        return super().update(instance, validated_data)

#通用樣板關係
class GenericTemplateRelationSerializer(serializers.ModelSerializer): #通用樣板關係序列器

    class Meta:
        model = GenericTemplate #指定序列器所用的Model
        fields = ['templateId', 'templateType', 'nfvoType'] #指定此序列器唯讀時包含的欄位


class SliceTemplateRelationSerializer(serializers.ModelSerializer):
    genericTemplates = GenericTemplateRelationSerializer(many=True, read_only=True)

    class Meta:
        model = SliceTemplate
        fields = '__all__'

    @property
    def data(self):
        serialized_data = super().data
        custom_representation = dict()
        for _ in serialized_data['genericTemplates']:
            if _['templateType'] not in custom_representation:
                custom_representation[_['templateType']] = list()
            custom_representation[_['templateType']].append(_['templateId'])
        serialized_data['genericTemplates'] = custom_representation
        return serialized_data


class SliceTemplateSerializer(serializers.ModelSerializer):

    class Meta:
        model = SliceTemplate
        fields = '__all__'

    def create(self, validated_data):
        return super().create(validated_data)


class ServiceMappingPluginSerializer(serializers.ModelSerializer):

    def __init__(self, *args, **kwargs):
        if 'context' in kwargs.keys():
            view = kwargs['context']['view']
            if view.action == 'list':
                self.Meta.fields = ['name', 'allocate_nssi', 'deallocate_nssi', 'pluginFile', 'nm_host', 'nfvo_host', 'subscription_host']
            elif view.action == 'retrieve':
                self.Meta.fields = ['name', 'allocate_nssi', 'deallocate_nssi', 'pluginFile', 'nm_host', 'nfvo_host', 'subscription_host']
            elif view.action == 'create':
                self.Meta.fields = ['name', 'pluginFile']
            elif view.action == 'update':
                self.Meta.fields = ['pluginFile']
            else:
                self.Meta.fields = '__all__'
        super().__init__(*args, **kwargs)

    class Meta:
        model = ServiceMappingPluginModel
        fields = '__all__'

    def create(self, validated_data):
        response_data = dict()
        zipfile_check = ['deallocate/main.py', 'config.yaml', 'allocate/main.py']
        # Extract Zip file
        with zipfile.ZipFile(validated_data['pluginFile']) as _zipfile:
            for file in _zipfile.filelist:
                if file.filename in zipfile_check:
                    zipfile_check.remove(file.filename)
            if not zipfile_check:
                _zipfile.extractall(path=os.path.join(
                                    settings.PLUGIN_ROOT, validated_data['name']))
        # Assign Plugin config
        if not zipfile_check:
            with open(os.path.join(settings.PLUGIN_ROOT, validated_data['name'],
                                   'config.yaml')) as stream:
                config = yaml.safe_load(stream)
                validated_data = {
                    'name': validated_data['name'],
                    'allocate_nssi': config['allocate_file'],
                    'deallocate_nssi': config['deallocate_file'],
                    'nm_host': config['nm_ip'],
                    'nfvo_host': config['nfvo_ip'],
                    'subscription_host': config['kafka_ip'],
                    'pluginFile': validated_data['pluginFile']
                }
                self.Meta.fields = '__all__'
            return super().create(validated_data)
        response_data['status'] = PluginOperationStatus.ERROR
        raise Exception(response_data)

    def update(self, instance, validated_data):
        response_data = dict()
        zipfile_check = ['deallocate/main.py', 'config.yaml', 'allocate/main.py']
        
        # Extract Zip file
        with zipfile.ZipFile(validated_data['pluginFile']) as _zipfile:
            for file in _zipfile.filelist:
                if file.filename in zipfile_check:
                    zipfile_check.remove(file.filename)
            if not zipfile_check:
                _zipfile.extractall(path=os.path.join(
                    settings.PLUGIN_ROOT, instance.name))
        # Assign Plugin config
        if not zipfile_check:
            with open(os.path.join(settings.PLUGIN_ROOT, instance.name,
                                   'config.yaml')) as stream:
                config = yaml.safe_load(stream)
                validated_data = {
                    'allocate_nssi': config['allocate_file'],
                    'deallocate_nssi': config['deallocate_file'],
                    'nm_host': config['nm_ip'],
                    'nfvo_host': config['nfvo_ip'],
                    'subscription_host': config['kafka_ip'],
                    'pluginFile': validated_data['pluginFile']
                }
                self.Meta.fields = '__all__'
                instance.pluginFile.delete()
                return super().update(instance, validated_data)
        response_data['status'] = PluginOperationStatus.ERROR
        raise Exception(response_data)


class ServiceMappingPluginRelationSerializer(serializers.ModelSerializer):
    genericTemplates = GenericTemplateRelationSerializer(many=True, read_only=True)
    nfvoType = ServiceMappingPluginSerializer(many=True, read_only=True)

    class Meta:
        model = SliceTemplate
        fields = '__all__'

    @property
    def data(self):
        serialized_data = super().data
        custom_representation = dict()
        for _ in serialized_data['genericTemplates']:
            if _['templateType'] not in custom_representation:
                custom_representation[_['templateType']] = list()
            custom_representation[_['templateType']].append(_['templateId'])
        serialized_data['genericTemplates'] = custom_representation
        return serialized_data
