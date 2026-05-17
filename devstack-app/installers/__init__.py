# DevStack App Installers Package
from .wordpress import WordPressInstaller
from .drupal import DrupalInstaller
from .custom_php import CustomPHPInstaller
from .laravel import LaravelInstaller

ALL_INSTALLERS = [
    WordPressInstaller,
    DrupalInstaller,
    CustomPHPInstaller,
    LaravelInstaller,
]
