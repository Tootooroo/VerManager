from django.test import TestCase
from django.http import HttpRequest
from django.template.loader import render_to_string

from manager.views import index, verManagerPage

from manager.master.verControl import RevSync
from manager.master.workerRoom import WorkerRoom
from manager.basic.letter import *
from manager.master.eventListener import EventListener
from manager.master.worker import Task

from manager.master.dispatcher import Dispatcher

from manager.basic.util import spawnThread

from manager.master.master import ServerInst
from manager.worker.client import Client


import time
import unittest
import socket

# Create your tests here.
from manager.master.verControl import VerControlTestCases
from manager.basic.letter import letterTest
from manager.master.dispatcher import DispatcherUnitTest
from manager.basic.info import InfoTestCases
from manager.master.logger import LoggerTestCases
from manager.basic.storage import StorageTestCases
from manager.master.build import BuildTestCases
from manager.master.task import TaskTestCases
from manager.basic.observer import ObTestCases
from manager.worker.postListener import PostListenerTestCases
from manager.master.worker import WorkerTestCases
