from __future__ import absolute_import
from importlib import import_module
from os import path, environ
import json
import os
from flask import Flask, Blueprint, abort, jsonify, request, session, make_response
import sys
import settings
from celery import Celery

app = Flask(__name__)
app.config.from_object(settings)


def make_celery(app):
    celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    return celery


celery = make_celery(app)


@celery.task(name="tasks.start_script")
def start_script(script):
    s = import_module('scripts.' + script)
    return s.run()


@app.route("/script/<script>/")
def script(script):
    res = start_script.apply_async(script, )
    return make_response('<a href="http://localhost:5000/script/result/' + res.task_id + '">result</a>')


@app.route("/script/result/<task_id>")
def show_script_result(task_id):
    retval = start_script.AsyncResult(task_id).get(timeout=1.0)
    return repr(retval)


if __name__ == "__main__":
    port = int(environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
