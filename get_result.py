import datetime
from OpsManage.Utils.send_message import send_dingding_message
from OpsManage.models import tb_userinfo_batch, tb_userinfo_result
from OpsManage.Utils.JsonResponse import JsonResponse
from OpsManage.serializers import tb_userinfo_batchSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet
from Restful_sql.Event_Manage.event_manage import get_event_info
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning


class ResultView(GenericViewSet):
    permission_classes = [IsAuthenticated]
    queryset = tb_userinfo_batch.objects.filter()
    serializer_class = tb_userinfo_batchSerializer
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)  # 防止warning

    def get_result(self, request):
        batch_code = request.data.get("Args").get("batchcode")
        if not tb_userinfo_result.objects.filter(batchcode=batch_code):
            return JsonResponse(success=False, data=[], message='该批次号不存在')
        datastatus = tb_userinfo_batch.objects.get(batchcode=batch_code).datastatus
        res_query = tb_userinfo_result.objects.filter(batchcode=batch_code)
        leaderid = request.data.get("Args").get("opercode")
        data = []
        return_dict = {}
        datatype = request.data.get("Args").get("datatype").upper()
        if datastatus == 2:
            if datatype == "UID":
                for numb, obj in enumerate(res_query):
                    context = {
                        "id": numb + 1,
                        "batchcode": batch_code,
                        "userid": obj.userid,
                        "mobile": obj.mobile,
                        "username": obj.username,
                        "idcard": obj.idcard,
                    }
                    data.append(context)
            else:
                for numb, obj in enumerate(res_query):
                    context = {
                        "id": numb + 1,
                        "batchcode": batch_code,
                        "mobile": obj.mobile,
                        "userid": obj.userid,
                    }
                    data.append(context)
            total_num = len(data)
            return_dict["rows"] = data
            self.backup_result_to_dingding(batch_code, "7572,5213", total_num)

            return JsonResponse(success=True, data=return_dict, message='获取成功')
        else:
            total_num = 0
            self.backup_result_to_dingding(batch_code, "7572,5213", total_num)
            return JsonResponse(success=False, data=data, message='数据正在处理中，请稍等')

    def backup_result_to_dingding(self, batchcode, leaderid, total_num):
        backup_info = tb_userinfo_batch.objects.get(batchcode=batchcode)
        datatype = "UID" if backup_info.datatype == "UID" else "MOBILE"
        datastatus = backup_info.datastatus
        oper_time = datetime.datetime.now().strftime('%Y-%m-%d')
        for userid in leaderid.split(","):
            userid = userid
            if datastatus == 2:
                event_code = "security_self_service_query_succ"
                xinge_content = get_event_info(event_code).prompt_template % (
                    oper_time, backup_info.opername, datatype, batchcode, total_num)
            else:
                event_code = "security_self_service_query_fail"
                xinge_content = get_event_info(event_code).prompt_template % (
                    oper_time, backup_info.opername, datatype, batchcode)
            send_dingding_message(event_code, xinge_content, userid)
