import datetime
from socket import *
from OpsManage.models import tb_userinfo_batch, Dic_common_conf
from OpsManage.Utils.JsonResponse import JsonResponse
from OpsManage.serializers import tb_userinfo_batchSerializer, tb_userinfo_resultSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning


class InfoBatchCodeView(GenericViewSet):
    permission_classes = [IsAuthenticated]
    queryset = tb_userinfo_batch.objects.filter()
    serializer_class = tb_userinfo_batchSerializer
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)  # 防止warning

    def send_command(self, data):
        data = str(data.__len__()) + "," + data
        HOST = '10.30.123.11'
        PORT = 30000
        BUFFSIZE = 1024000
        ADDR = (HOST, PORT)
        tctimeClient = socket(AF_INET, SOCK_STREAM)
        tctimeClient.connect(ADDR)
        tctimeClient.sendall(data.encode())
        Revdata = tctimeClient.recv(BUFFSIZE).decode()

        tctimeClient.close()
        return Revdata

    def sqlserver_scriptcheck(self, batch_code):
        return_dict = "<senddata>"
        return_dict = return_dict + "<operation>SearchUserInfo</operation>"
        return_dict = return_dict + "<orderNo>" + batch_code + "</orderNo>"
        return_dict = return_dict + '</senddata>'
        result = self.send_command(return_dict)
        return result

    def create_batch_code(self, request):
        datatype = request.data.get("Args").get("datatype").upper()
        prefix = "UID" if datatype == "UID" else "MOBILE"
        date_now = datetime.datetime.now().strftime('%Y%m%d')
        batch = prefix + date_now
        exits_batch = tb_userinfo_batch.objects.filter(batchcode__icontains=batch).order_by("-id")
        if not exits_batch:
            num = 1
            batch = '000' + str(num)
            batch_code = prefix + date_now + batch
        else:
            exits_batch_now = exits_batch[0].batchcode
            num = int(exits_batch_now[-4:]) + 1
            batch = str(num).zfill(4)
            batch_code = prefix + date_now + batch
        return batch_code

    def Info_Result_View(self, request):
        batch_code = self.create_batch_code(request)
        datatype = request.data.get("Args").get("datatype").upper()
        input_data = request.data.get("Args").get("input")
        if datatype == "UID":
            for uid in input_data:
                userid = uid
                context = {
                    "userid": userid,
                    "batchcode": batch_code
                }
                data = request.data.get("Args")
                data.update(context)
                serializer = tb_userinfo_resultSerializer(data=data)
                serializer.is_valid(raise_exception=True)
                serializer.save()
        else:
            for mob in input_data:
                mobile = mob
                context = {
                    "mobile": mobile,
                    "batchcode": batch_code
                }
                data = request.data.get("Args")
                data.update(context)
                serializer = tb_userinfo_resultSerializer(data=data)
                serializer.is_valid(raise_exception=True)
                serializer.save()
        return batch_code

    def Info_Batch_View(self, request):
        whitelist = Dic_common_conf.objects.filter(prop_code='userinfo_search')[0].prop_value
        userid = request.data.get("Args").get("opercode")
        if userid not in whitelist.split(","):
            return JsonResponse(success=False, data=[], message='您没有查询权限，请联系管理员')

        batch_code = self.Info_Result_View(request)

        data = request.data.get("Args")
        context = {
            "batchcode": batch_code
        }
        data.update(context)
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        self.sqlserver_scriptcheck(batch_code)

        return JsonResponse(success=True, data={"batchcode": batch_code}, message='获取批次号')
