"""
Mock module of test pix objects
"""
from pix import register, PIXObject


@register('PIXTestObj')
class PIXTestObj(PIXObject):
    def get_one(self):
        return 1


@register('PIXTestChildObj')
class PIXTestChildObj(PIXObject):
    pass
