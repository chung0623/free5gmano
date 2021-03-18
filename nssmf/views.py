# Copyright 2020 free5gmano
# All Rights Reserved.
#
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

#插入需要套件
import os
import yaml
import json #json模組
import shutil #shutil模組提供了一系列對文件和文件集合的高階操作。特別是提供了一些支持文件拷貝和刪除的函數。
import zipfile #Zip模組
import importlib #importlib模組的目的有兩個。第一個目的是在Python源代碼中提供import語句的實現（並且因此而擴展__import__()函數）。這提供了一個可移植到任何Python解釋器的import實現。相比使用Python以外的編程語言實現方式，這一實現更加易於理解。
                 #第二個目的是實現import的部分被公開在這個包中，使得用戶更容易創建他們自己的自定義對象(通常被稱為importer )來參與到導入過程中。

#插入框架需要套件
from django.http import JsonResponse, Http404, HttpResponse
from rest_framework.response import Response
from rest_framework import status, mixins
from rest_framework.decorators import action #REST Framework提供list,create,retrieve,update,partial_update,destroy等操作
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token

#插入 Model, Serializer, Enums
from nssmf.serializers import SliceTemplateSerializer, SliceTemplateRelationSerializer, \
    GenericTemplateSerializer, GenericTemplateFileSerializer, ServiceMappingPluginSerializer, \
    ServiceMappingPluginRelationSerializer
from nssmf.models import SliceTemplate, GenericTemplate, ServiceMappingPluginModel, Content
from nssmf.enums import OperationStatus, PluginOperationStatus
from free5gmano import settings

#身分驗證
class CustomAuthToken(ObtainAuthToken): 

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return JsonResponse({
            'token': token.key,
            'user_id': user.pk,
            'email': user.email
        })

#利用basename與action來做url的分流
class MultipleSerializerViewSet(ModelViewSet):
    def get_serializer_class(self):
        if self.basename == 'GenericTemplate': 
            if self.action == 'upload':
                return GenericTemplateFileSerializer
            return GenericTemplateSerializer 
        elif self.basename == 'SliceTemplate':
            if self.action in ('retrieve', 'list'):
                return SliceTemplateRelationSerializer
            return SliceTemplateSerializer
        elif self.basename == 'Provisioning':
            return SliceTemplateSerializer

#通用樣板
class GenericTemplateView(MultipleSerializerViewSet): 
    """ Generic Template
    """
    queryset = GenericTemplate.objects.all() #用queryset抓取GenericTemplate的Model資料
    serializer_class = MultipleSerializerViewSet.get_serializer_class #用serializer_class抓取Serializer中對應的資料，因為get_serializer_class有判斷式，因此會自動抓取對應資料

    @staticmethod
    def check(request, content, filename):
        # Check content isn't exist Content
        for query in Content.objects.all(): #迴圈query抓取Content的資料
            if str(content['topology_template']) in query.topology_template and \ #如果content的topology_template欄位轉成的字串在 query 的 topology_templatey 資料集中
                    request.data['nfvoType'] in query.templateId.nfvoType: #以及 request 的 nfvoType 欄位的值在 query 的 templateId.nfvoType 欄位資料中
                response = {
                    OperationStatus.OPERATION_FAILED: request.data[
                                                          'templateType'] + ' is exist ' + filename} #若上述條件成立，則 response 為 Enums OperationStatus 的 OPERATION_FAILED
                return response #返回response值

    def list(self, request, *args, **kwargs):
        """
            Query Generic Template information.

            The GET method queries the information of the Generic Template matching the filter.
        """
        return super().list(request, *args, **kwargs) #利用super()呼叫GenericTemplateView基礎類別MultipleSerializerViewSet的get_serializer_class方法，使用list

    def create(self, request, *args, **kwargs):
        """
            Create a new individual Generic Template resource.

            The POST method creates a new individual Generic Template resource.
        """
        return super().create(request, *args, **kwargs) #利用super()呼叫GenericTemplateView基礎類別MultipleSerializerViewSet的get_serializer_class方法，使用create

    def retrieve(self, request, *args, **kwargs):
        """
            Read information about an individual Generic Template resource.

            The GET method reads the information of a Generic Template.
        """
        return super().retrieve(request, *args, **kwargs) #利用super()呼叫GenericTemplateView基礎類別MultipleSerializerViewSet的get_serializer_class方法，使用retrieve

    def update(self, request, *args, **kwargs):
        """
            Update information about an individual Generic Template resource.

            The PATCH method updates the information of a Generic Template.
        """
        return super().update(request, *args, **kwargs) #利用super()呼叫GenericTemplateView基礎類別MultipleSerializerViewSet的get_serializer_class方法，使用update

    def destroy(self, request, *args, **kwargs):
        """
            Delete an individual Generic Template.

            The DELETE method deletes an individual Generic Template resource.
        """
        file = self.get_object().templateFile #self.get_object().templateFile抓取GenericTemplate Model的templateFile
        if file:
            file_folder = os.path.join( #利用os.path.join()函數，組合多個路徑，以抓取完整檔案路徑
                settings.MEDIA_ROOT, #有了上面這個路由設置，我們就可以在瀏覽器的地址欄根據media文件夾中文件的路徑去訪問對應的文件了
                os.path.dirname(str(self.get_object().templateFile)),
                str(self.get_object().templateId)
            )
            shutil.rmtree(file_folder) #shutil.rmtree path指向file_folder目錄，刪除整個資料夾樹，也就是，它可以刪除資料夾下的所有檔案和子資料夾。
            file.delete()
        return super().destroy(request, *args, **kwargs)

    def upload(self, request, *args, **kwargs):
        """
            Upload a Generic Template by providing the content of the Generic Template.

            The PUT method uploads the content of a Generic Template.
        """
        path = os.path.join( #利用os.path.join()函數，組合多個路徑，以抓取完整檔案路徑
            settings.MEDIA_ROOT, #有了上面這個路由設置，我們就可以在瀏覽器的地址欄根據media文件夾中文件的路徑去訪問對應的文件了
            request.data['templateType'],
            str(kwargs['pk'])
        )
        generic_template_obj = self.get_object()
        # Delete old Content related
        for relate_obj in self.get_object().content_set.all(): #查看關聯的內容數據
            file = self.get_object().templateFile
            file.delete()
            self.get_object().content_set.remove(relate_obj) #刪除舊的關聯資料
            
        with zipfile.ZipFile(request.data['templateFile']) as _zipfile: #利用zipfile.ZipFile()函數將request.data['templateFile']轉為zip檔，並宣告為_zipfile
            for element in _zipfile.namelist(): #宣告element在_zipFile.namelist()函數所獲取的該zip檔所有檔案資訊
                if '.yaml' in element: #若element含有yaml檔
                    with _zipfile.open(element) as file: #zipfile.open()以二進製文件類對象的形式訪問一個歸檔成員。name可以是歸檔內某個文件的名稱也可以是某個ZipInfo對象
                        content = yaml.load(file, Loader=yaml.FullLoader) #宣告content為yaml.load()函數得到file的內容
                        content_obj = Content(type=self.get_object().templateType, #宣告content_obj為Content Model的資訊
                                              tosca_definitions_version=content['tosca_definitions_version'],
                                              topology_template=str(content['topology_template']))
                    # check_result = self.check(request, content, filename)

                    # if check_result:
                    #     return Response(check_result, status=400)

                    content_obj.save() #儲存content_obj
                    generic_template_obj.content_set.add(content_obj) #generic_template_obj新增content_obj
                elif '.json' in element: #若element含有json檔
                    with _zipfile.open(element) as file: #zipfile.open()以二進製文件類對象的形式訪問一個歸檔成員。name可以是歸檔內某個文件的名稱也可以是某個ZipInfo對象。
                        content = json.loads(file.read().decode('utf-8')) #content為file轉為utf-8格式的資料
                    content_obj = Content(type=self.get_object().templateType, #宣告content_obj為Content Model的資訊
                                          tosca_definitions_version="None",
                                          topology_template=str(content))
                    content_obj.save() #儲存content_obj
                    generic_template_obj.content_set.add(content_obj) #generic_template_obj新增content_obj
            _zipfile.extractall(path=path) #利用zipfile.extractall()來解壓縮zip檔
        self.partial_update(request, *args, **kwargs) #partial update()可以將request要求的修改完成後，傳到後台進行資料修改
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], url_path='example_download/(?P<example>(.)*)/(?P<path>(.)*)')
    def example_download(self, request, *args, **kwargs):
        """
            Download an individual Generic Template.

            The GET method reads the content of the Generic Template.
        """
        source_path = os.getcwd() #os.getcwd() 方法用於返回當前工作目錄。
        # download_query = self.queryset.filter(templateFile=kwargs['path'])
        # if download_query:
        #     with download_query[0].templateFile.open() as f:
        #         return HttpResponse(f.read(), content_type="application/zip")
        # else:
        example_file = os.path.join(settings.BASE_DIR, 'nssmf', 'template_example',
                                    kwargs['example'], kwargs['path'].split('/')[0])
        os.chdir(example_file) #e/ 更換路徑到example_file檔案目錄

        with zipfile.ZipFile(example_file + '.zip', mode='w',
                             compression=zipfile.ZIP_DEFLATED) as zf: #建立新檔案
            for root, folders, files in os.walk('.'):
                for s_file in files:
                    a_file = os.path.join(root, s_file)
                    zf.write(a_file)
        os.chdir(source_path)
        with open(example_file + '.zip', 'rb') as f:
            return HttpResponse(f.read(), content_type="application/zip")

    @action(detail=False, methods=['get'], url_path='download/(?P<path>(.)*)')
    def download(self, request, *args, **kwargs):
        """
            Download an individual Generic Template.

            The GET method reads the content of the Generic Template.
        """
        download_query = self.queryset.filter(templateFile=kwargs['path']) #宣告download_query為queryset中templateFile=kwargs['path']的資料
        s = download_query[0].templateFile.name #s為download_query[0]的templateFile.name
        filename = s[4:] #filename取最後四個以外元素的資料
        if download_query:
            with download_query[0].templateFile.open() as f:
                # return HttpResponse(f.read(), content_type="application/zip")
                response = HttpResponse(f.read(), content_type="application/zip")
                response['Content-Disposition'] = 'inline; filename=' + filename
                return response

#切片樣板
class SliceTemplateView(MultipleSerializerViewSet):
    """
        Slice Template
    """
    queryset = SliceTemplate.objects.all() #用queryset抓取GenericTemplate的Model資料
    serializer_class = MultipleSerializerViewSet.get_serializer_class #用serializer_class抓取Serializer中對應的資料，因為get_serializer_class有判斷式，因此會自動抓取對應資料

    def list(self, request, *args, **kwargs): 
        """
            Query Slice Template information.

            The GET method queries the information of the Slice Template matching the filter.
        """
        return super().list(request, *args, **kwargs) #利用super()呼叫SliceTemplateView基礎類別MultipleSerializerViewSet的get_serializer_class方法，使用list

    def create(self, request, *args, **kwargs):
        """
            Create a new individual Slice Template resource.

            The POST method creates a new individual Slice Template resource.
        """
        return super().create(request, *args, **kwargs) #利用super()呼叫SliceTemplateView基礎類別MultipleSerializerViewSet的get_serializer_class方法，使用create

    def retrieve(self, request, *args, **kwargs):
        """
            Read information about an individual Slice Template resource.

            The GET method reads the information of a Slice Template.
        """
        return super().retrieve(request, *args, **kwargs) #利用super()呼叫SliceTemplateView基礎類別MultipleSerializerViewSet的get_serializer_class方法，使用retrieve

    def update(self, request, *args, **kwargs):
        """
            Update information about an individual Slice Template resource.

            The PATCH method updates the information of a Slice Template.
        """
        return super().update(request, *args, **kwargs) #利用super()呼叫SliceTemplateView基礎類別MultipleSerializerViewSet的get_serializer_class方法，使用update

    def destroy(self, request, *args, **kwargs):
        """
            Delete an individual Slice Template.

            The DELETE method deletes an individual Slice Template resource.
        """
        return super().destroy(request, *args, **kwargs) #利用super()呼叫SliceTemplateView基礎類別MultipleSerializerViewSet的get_serializer_class方法，使用destroy


class ProvisioningView(GenericViewSet, mixins.CreateModelMixin, mixins.DestroyModelMixin):
    """ Provisioning Network Slice Instance
    """
    queryset = SliceTemplate.objects.all()
    serializer_class = ServiceMappingPluginRelationSerializer

    def create(self, request, *args, **kwargs):
        """
            Allocate Network Slice Subnet Instance.

            Allocate a new individual Network Slice Subnet Instance
        """
        data = request.data['attributeListIn']
        response_data = dict()
        try:
            response_data['status'] = OperationStatus.OPERATION_FAILED
            if data['using_existed']:
                check_query = SliceTemplate.objects.filter(instanceId=data['using_existed'])
                for query in check_query:
                    query.instanceId.remove(data['using_existed'])
            unit_query = SliceTemplate.objects.get(templateId=data['nsstid'])
            slice_serializer = ServiceMappingPluginRelationSerializer(unit_query)
            generic_templates = slice_serializer.data['genericTemplates']
            service_plugin = slice_serializer.data['nfvoType'][0]
        except SliceTemplate.DoesNotExist:
            print(SliceTemplate.DoesNotExist)
            return JsonResponse(response_data)
        try:
            parameter = {
                'vnf_template': generic_templates['VNF'][0],
                'ns_template': generic_templates['NSD'][0],
                'slice_template': generic_templates['NRM'][0],
                'use_existed': data['using_existed']
            }
            plugin = importlib.import_module(
                'nssmf.plugin.{}.{}.{}'.format(
                    service_plugin['name'],
                    service_plugin['allocate_nssi'].split('/')[0],
                    service_plugin['allocate_nssi'].split('/')[1].split('.')[0]))
            nfvo_plugin = plugin.NFVOPlugin(
                        service_plugin['nm_host'],
                        service_plugin['nfvo_host'],
                        service_plugin['subscription_host'],
                        parameter)
            nfvo_plugin.allocate_nssi()
            unit_query.instanceId.add(nfvo_plugin.nssiId)
            return JsonResponse(nfvo_plugin.moi_config)
        except IOError as e:
            return JsonResponse(response_data, status=400)

    def destroy(self, request, *args, **kwargs):
        """
            Deallocate Network Slice Subnet Instance.

            Deallocate a new individual Network Slice Subnet Instance
        """
        response_data = dict()
        response_data['status'] = OperationStatus.OPERATION_FAILED
        try:
            slice_id = kwargs['pk']
            if self.get_queryset().filter(instanceId=slice_id):
                response_data['status'] = OperationStatus.OPERATION_SUCCEEDED
                unit_query = self.get_queryset().filter(instanceId=slice_id)[0]
                slice_serializer = self.get_serializer(unit_query)
                service_plugin = slice_serializer.data['nfvoType'][0]
                parameter = {
                    'slice_template': slice_serializer.data['templateId'],
                    'slice_instance': slice_id,
                    'mano_template': False
                }
                plugin = importlib.import_module(
                    'nssmf.plugin.{}.{}.{}'.format(
                        service_plugin['name'],
                        service_plugin['deallocate_nssi'].split('/')[0],
                        service_plugin['deallocate_nssi'].split('/')[1].split('.')[0]))
                nfvo_plugin = plugin.NFVOPlugin(service_plugin['nm_host'],
                                                service_plugin['nfvo_host'],
                                                service_plugin['subscription_host'],
                                                parameter)
                nfvo_plugin.deallocate_nssi()
                unit_query.instanceId.remove(slice_id)
                return JsonResponse(response_data)
            else:
                return JsonResponse(response_data, status=400)
        except TypeError:
            return JsonResponse(response_data, status=400)

class ServiceMappingPluginView(ModelViewSet):
    """ Service Mapping Plugin framework
    """
    queryset = ServiceMappingPluginModel.objects.all()
    serializer_class = ServiceMappingPluginSerializer
    response_data = dict()

    def list(self, request, *args, **kwargs):
        """
            Read information about an individual Service Mapping Plugin resource.

            The GET method reads the information of a Service Mapping Plugin.
        """
        return super().list(self, request, args, kwargs)

    def create(self, request, *args, **kwargs):
        """
            Create a new individual Service Mapping Plugin resource.

            The POST method creates a new individual Service Mapping Plugin resource.
        """
        return super().create(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """
            Query Service Mapping Plugin information.

            The GET method queries the information of the Service Mapping Plugin \
            matching the filter.
        """
        return super().retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        """
            Update information about an individual Service Mapping Plugin resource.

            The PATCH method updates the information of a Service Mapping Plugin.
        """
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """
            Delete an individual Service Mapping Plugin.

            The DELETE method deletes an individual Service Mapping Plugin resource.
        """
        self_object = self.get_object()
        file = self_object.pluginFile
        if file:
            file_folder = os.path.join(
                settings.PLUGIN_ROOT,
                self_object.name
            )
            shutil.rmtree(file_folder)
            file.delete()
        super().destroy(self, request, args, kwargs)
        self.response_data['status'] = PluginOperationStatus.DELETE
        return JsonResponse(self.response_data, status=200)

    @action(detail=False, methods=['get'], url_path='download/(?P<name>(.)*)/(?P<filename>(.)*)')
    def download(self, request, *args, **kwargs):
        """
            Download an individual Service Mapping Plugin.

            The GET method reads the content of the Service Mapping Plugin.
        """
        try:
            plugin_obj = ServiceMappingPluginModel.objects.get(name=kwargs['name'])
            with plugin_obj.pluginFile.open() as f:
                response = HttpResponse(f.read(), content_type="application/zip")
                response['Content-Disposition'] = 'inline; filename=' + kwargs['filename']
                return response
        except IOError:
            raise Http404
