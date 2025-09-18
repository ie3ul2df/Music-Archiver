from django.template import Context, Template
from django.test import SimpleTestCase


class RatingStarsTemplateTests(SimpleTestCase):
    def render_stars(self, avg):
        template_string = (
            "{% load rating_extras %}{% include 'ratings/_stars.html' with type='track' id=1 avg=avg count=2 user_rating=None %}"
        )
        template = Template(template_string)
        return template.render(Context({"avg": avg}))

    def test_string_average_highlights_expected_stars(self):
        html = self.render_stars("4.0")
        self.assertIn('class="star-btn is-selected"', html)

    def test_non_numeric_average_defaults_to_zero(self):
        html = self.render_stars("not-a-number")
        self.assertNotIn('class="star-btn is-selected"', html)