"""
LiqPay Python3 SDK
~~~~~~~~~~~~~~~~~
supports python 3.4.x, 3.5.x, 3.6.x, 3.7.x version
requires requests module
"""

__title__ = 'LiqPay Python3 SDK'
__version__ = '1.1.2'

import base64
from copy import deepcopy
import hashlib
import json
from urllib.parse import urljoin

import requests


def to_unicode(s):
    """
    :param s:
    :return: unicode value (decoded utf-8)
    """
    if isinstance(s, str):
        return s

    if isinstance(s, bytes):
        return s.decode('utf8', 'strict')

    if hasattr(s, '__str__'):
        return s.__str__()

    return str(bytes(s), 'utf-8', 'strict')


class ParamValidationError(Exception):
    pass


class LiqPay(object):
    FORM_TEMPLATE = u'''\
<form method="post" action="{action}" accept-charset="utf-8">
\t{param_inputs}
    <input type="image" src="//static.liqpay.ua/buttons/p1{language}.radius.png" name="btn_text" />
</form>'''
    INPUT_TEMPLATE = u'<input type="hidden" name="{name}" value="{value}"/>'

    SUPPORTED_PARAMS = [
        'public_key', 'amount', 'currency', 'description', 'order_id',
        'result_url', 'server_url', 'type', 'signature', 'language', 'sandbox'
    ]

    def __init__(self, public_key, private_key, host='https://www.liqpay.ua/api/'):
        self._public_key = public_key
        self._private_key = private_key
        self._host = host

    def _make_signature(self, *args):
        joined_fields = ''.join(to_unicode(x) for x in args).encode('utf8')
        return base64.b64encode(hashlib.sha1(joined_fields).digest())

    def _prepare_params(self, params):
        params = {} if params is None else deepcopy(params)
        params.update(public_key=self._public_key)
        return params

    def api(self, url, params=None):
        params = self._prepare_params(params)

        json_encoded_params = json.dumps(params)
        private_key = self._private_key
        signature = self._make_signature(private_key, json_encoded_params, private_key)

        request_url = urljoin(self._host, url)
        request_data = {'data': json_encoded_params, 'signature': signature}
        response = requests.post(request_url, data=request_data, verify=False)
        return json.loads(response.content.decode('utf8'))

    def cnb_form(self, params):
        params = self._prepare_params(params)
        params_validator = (
            ('amount', lambda x: x is not None and float(x) > 0),
            ('description', lambda x: x is not None)
        )
        for key, validator in params_validator:
            if validator(params.get(key)):
                continue

            raise ParamValidationError('Invalid param: "%s"' % key)

        # spike to set correct values for language, currency and sandbox params
        language = params.get('language', 'ru')
        currency = params['currency']
        params.update(
            language=language,
            currency=currency if currency != 'RUR' else 'RUB',
            sandbox=int(bool(params.get('sandbox')))
        )
        params_templ = {'data': base64.b64encode(json.dumps(params).encode('utf8'))}
        params_templ['signature'] = self._make_signature(self._private_key, params_templ['data'], self._private_key)
        form_action_url = urljoin(self._host, '3/checkout/')
        format_input = lambda k, v: self.INPUT_TEMPLATE.format(name=k, value=to_unicode(v))
        inputs = [format_input(k, v) for k, v in params_templ.items()]
        return self.FORM_TEMPLATE.format(
            action=form_action_url,
            language=language,
            param_inputs=u'\n\t'.join(inputs)
        )

    def cnb_signature(self, params):
        params = self._prepare_params(params)
        return self._make_signature(self._private_key, base64.b64encode(json.dumps(params).encode('utf8')), self._private_key)

    def str_to_sign(self, str):
        return base64.b64encode(hashlib.sha1(str.encode('utf8')).digest())