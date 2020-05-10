from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired

class AuthForm(FlaskForm):
    auth = StringField('Authorization Code', validators=[DataRequired()])
    icalURL = StringField('External Calendar Link', validators=[DataRequired()])
    submit = SubmitField('Submit')