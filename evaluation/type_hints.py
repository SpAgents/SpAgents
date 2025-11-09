# -*- coding: utf-8 -*-
"""
类型提示文件 - 解决IDE警告问题
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # 这些导入只是为了IDE的类型检查
    import sys
    import time
    import os
    import uuid
    import json
    import io
    import traceback
    import numpy as np
    import pandas as pd
    from flask import Flask, request, Response
    from flask_cors import CORS 