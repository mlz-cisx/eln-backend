import logging
import sys
from jaeger_logger_reporter import LoggerTraceConfig, LoggerTracerReporter
from joeseln_backend.conf.base_conf import JAEGER_PORT, JAEGER_HOST, \
    JAEGER_SERVICE_NAME


def jaeger_tracer():
    config = LoggerTraceConfig(
        config={
            'sampler': {
                'type': 'const',
                'param': 1,
            },
            'local_agent': {
                'reporting_host': JAEGER_HOST,
                'reporting_port': JAEGER_PORT,
            },
            'logging': True,
            'max_tag_value_length': sys.maxsize
        },
        service_name=JAEGER_SERVICE_NAME,
        validate=True,
    )

    # setup my logger (optional)
    tracer_logger = logging.getLogger('eln_jaeger_logger')
    tracer_logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '[%(levelname)s][%(date)s] %(name)s %(span)s %(event)s %(message)s')
    handler.setFormatter(formatter)
    handler.setLevel(logging.DEBUG)
    tracer_logger.addHandler(handler)
    tracer = config.initialize_tracer(
        logger_reporter=LoggerTracerReporter(logger=tracer_logger))

    return tracer
