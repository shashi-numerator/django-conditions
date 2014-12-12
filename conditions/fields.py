"""
:Created: 6 December 2014
:Author: Lucas Connors

"""

from django import forms
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from jsonfield.fields import JSONField, JSONFormField, JSONWidget

from .exceptions import InvalidConditionError
from .lists import CondList


__all__ = ['ConditionsWidget', 'ConditionsFormField', 'ConditionsField']


class ConditionsWidget(JSONWidget):
    template_name = 'conditions_widget.html'

    def __init__(self, *args, **kwargs):
        self.condition_definitions = kwargs.pop('condition_definitions', {})
        if 'attrs' not in kwargs:
            kwargs['attrs'] = {}
        if 'cols' not in kwargs['attrs']:
            kwargs['attrs']['cols'] = 100
        super(ConditionsWidget, self).__init__(*args, **kwargs)

    def render(self, name, value, attrs=None):
        if isinstance(value, CondList):
            value = value.encode()
        textarea = super(ConditionsWidget, self).render(name, value, attrs)
        conditions = []
        for groupname, group in self.condition_definitions.iteritems():
            conditions_in_group = sorted(
                [(condstr, condition.help_text(), condition.full_description()) for condstr, condition in group.iteritems()],
                key=lambda x: x[0]
            )
            conditions.append((groupname, conditions_in_group))
        conditions = sorted(conditions, key=lambda x: x[0])

        context = {
            'textarea': textarea,
            'conditions': conditions,
        }

        return mark_safe(render_to_string(self.template_name, context))


class ConditionsFormField(JSONFormField):

    def __init__(self, *args, **kwargs):
        self.condition_definitions = kwargs.pop('condition_definitions', {})
        if 'widget' not in kwargs:
            kwargs['widget'] = ConditionsWidget(condition_definitions=self.condition_definitions)
        super(ConditionsFormField, self).__init__(*args, **kwargs)

    def clean(self, value):
        """ Validate conditions by decoding result """
        cleaned_json = super(ConditionsFormField, self).clean(value)
        if cleaned_json is None: return

        try:
            CondList.decode(cleaned_json, definitions=self.condition_definitions)
        except InvalidConditionError as e:
            raise forms.ValidationError(
                "Invalid conditions JSON: {error}".format(error=str(e))
            )
        else:
            return cleaned_json


class ConditionsField(JSONField):
    """
    ConditionsField stores information on when the "value" of the
    instance should be considered True.
    """

    def __init__(self, *args, **kwargs):
        self.condition_definitions = kwargs.pop('definitions', {})
        super(ConditionsField, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        kwargs['condition_definitions'] = self.condition_definitions
        return ConditionsFormField(**kwargs)

    def pre_init(self, value, obj):
        value = super(ConditionsField, self).pre_init(value, obj)
        if isinstance(value, dict):
            value = CondList.decode(value, definitions=self.condition_definitions)
        return value

    def dumps_for_display(self, value):
        if isinstance(value, CondList):
            value = value.encode()
        return super(ConditionsField, self).dumps_for_display(value)

    def get_db_prep_value(self, value, connection, prepared=False):
        if isinstance(value, CondList):
            value = value.encode()
        return super(ConditionsField, self).get_db_prep_value(value, connection, prepared)


# Introspection rules required by south
# Read more here: http://south.aeracode.org/wiki/MyFieldsDontWork
try:
    from south.modelsinspector import add_introspection_rules
except ImportError:
    pass
else:
    add_introspection_rules([], ["^conditions\.fields\.ConditionsField"])