import io
import base64
import zlib
from flask import Flask, send_file, make_response, jsonify
from blockdiag.command import BlockdiagApp
from seqdiag.command import SeqdiagApp
from nwdiag.command import NwdiagApp
from actdiag.command import ActdiagApp
from backend.diag import generate_diag
from backend.error import GenerateError

application = Flask(__name__)


class InvalidUsage(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv


def _generate_diagram(app, diagram_type, output_format, source_encoded):
    result = generate_diag(app, diagram_type, output_format, source_encoded)
    output_format = output_format.lower()
    if output_format == 'png':
        response = send_file(io.BytesIO(result),
                             attachment_filename='result.png',
                             mimetype='image/png')
        return response
    elif output_format == 'pdf':
        response = make_response(result)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'inline; filename=%s.pdf' % 'result'
        return response
    elif output_format == 'svg':
        response = make_response(result)
        response.headers["Content-Type"] = "image/svg+xml; charset=utf-8"
        return response
    else:
        raise InvalidUsage('Unsupported output format: %s. Must be one of: png, svg or pdf.',
                           status_code=400)


@application.route('/blockdiag/<string:output_format>/<string:source_encoded>')
def blockdiag(output_format, source_encoded):
    return _generate_diagram(BlockdiagApp(), 'block', output_format, source_encoded)


@application.route('/seqdiag/<string:output_format>/<string:source_encoded>')
def seqdiag(output_format, source_encoded):
    return _generate_diagram(SeqdiagApp(), 'sequence', output_format, source_encoded)


@application.route('/actdiag/<string:output_format>/<string:source_encoded>')
def actdiag(output_format, source_encoded):
    return _generate_diagram(ActdiagApp(), 'activity', output_format, source_encoded)


@application.route('/nwdiag/<string:output_format>/<string:source_encoded>')
def nwdiag(output_format, source_encoded):
    return _generate_diagram(NwdiagApp(), 'network', output_format, source_encoded)


@application.route('/<string:output_format>/<string:source_encoded>')
def diag(output_format, source_encoded):
    source = zlib.decompress(base64.urlsafe_b64decode(source_encoded.encode('ascii'))).lstrip()
    if source.startswith('blockdiag'):
        return blockdiag(output_format, source_encoded)
    elif source.startswith('seqdiag'):
        return seqdiag(output_format, source_encoded)
    elif source.startswith('actdiag'):
        return actdiag(output_format, source_encoded)
    elif source.startswith('nwdiag'):
        return nwdiag(output_format, source_encoded)
    else:
        raise InvalidUsage('Diagram source must begin with one of the following: blockdiag, seqdiag, actdiag or nwdiag',
                           status_code=400)


@application.errorhandler(GenerateError)
def handle_generate_error(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


@application.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


if __name__ == '__main__':
    application.run(debug=True, host='0.0.0.0', port=8001)
