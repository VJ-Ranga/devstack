# DevStack App Installers Package
from .wordpress import WordPressInstaller
from .drupal import DrupalInstaller

ALL_INSTALLERS = [
    WordPressInstaller,
    DrupalInstaller
]
