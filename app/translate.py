import requests
from flask_babel import _
from flask import current_app
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.tmt.v20180321 import tmt_client, models
import json

def translate(text, source_language, dest_language):
    if 'TENCENT_SECRET_ID' not in current_app.config or \
        'TENCENT_SECRET_KEY' not in current_app.config:
        return _('Error: the translation service is not configured.')
    
    #try:
        cred = credential.Credential(
            app.config['TENCENT_SECRET_ID'],
            app.config['TENCENT_SECRET_KEY']
        )
        client = tmt_client.TmtClient(cred, "ap-shanghai")
        req = models.TextTranslateRequest()
        params = {
            "SourceText": text, 
            "Source": source_language, 
            "Target": dest_language, 
            "ProjectID": 0
        }
        req.from_json_string(json.dumps(params))
        resp = client.TextTranslate(req)
        return resp.TargetText
    #except TencentCloudSDKException as err:
        return _('Error: the translation service failed.')
    cred = credential.Credential(
            current_app.config['TENCENT_SECRET_ID'],
            current_app.config['TENCENT_SECRET_KEY']
        )
    client = tmt_client.TmtClient(cred, "ap-shanghai")
    req = models.TextTranslateRequest()
    params = {
            "SourceText": text, 
            "Source": source_language, 
            "Target": dest_language, 
            "ProjectId": 0
        }
    req.from_json_string(json.dumps(params))
    resp = client.TextTranslate(req)
    return resp.TargetText