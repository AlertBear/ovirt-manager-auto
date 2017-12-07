from art.test_handler.settings import ART_CONFIG as art_config

parameters = art_config["PARAMETERS"]
rest_connection = art_config["REST_CONNECTION"]
enums = art_config["elements_conf"]["RHEVM Enums"]

vdc_host = rest_connection["host"]
vdc_port = rest_connection["port"]
scheme = rest_connection.get("scheme")
product = parameters['product_name']

upstream_flag = 'ovirt' in product.lower()

OVIRT_ENGINE = "ovirt-engine"

WEB_IDS = {
    "release_notes": [
        "WelcomePage_releaseNotesHTML",
        "WelcomePage_releaseNotesPDF"
    ],
    "technical_notes": [
        "WelcomePage_technicalNotesHTML",
        "WelcomePage_technicalNotesPDF"
    ],
    "package_manifest": [
        "WelcomePage_packageManifestHTML",
        "WelcomePage_packageManifestPDF"
    ],
    "planning": [
        "WelcomePage_planningHTML",
        "WelcomePage_planningPDF"
    ],
    "installation_guide": [
        "WelcomePage_installationGuideHTML",
        "WelcomePage_installationGuidePDF"
    ],
    "selfhosted_installation_guide": [
        "WelcomePage_selfhosted_installationGuideHTML",
        "WelcomePage_selfhosted_installationGuidePDF"
    ],
    "upgrade_guide": [
        "WelcomePage_upgradeGuideHTML",
        "WelcomePage_upgradeGuidePDF"
    ],
    "intro_admin_guide": [
        "WelcomePage_intro_adminGuideHtml",
        "WelcomePage_intro_adminGuidePDF"
    ],
    "admin_guide": [
        "WelcomePage_adminGuideHtml",
        "WelcomePage_adminGuidePDF"
    ],
    "dwh_guide": [
        "WelcomePage_dwhGuideHtml",
        "WelcomePage_dwhGuidePDF"
    ],
    "userportal_guide": [
        "WelcomePage_userportalGuideHTML",
        "WelcomePage_userportalGuidePDF"
    ],
    "vm_guide": [
        "WelcomePage_vmGuideHTML",
        "WelcomePage_vmGuidePDF"
    ],
    "technical_reference": [
        "WelcomPage_technical_referenceHTML",
        "WelcomePage_technical_referencePDF"
    ],
    "restapi": [
        "WelcomePage_restapiHTML",
        "WelcomePage_restapiPDF"
    ],
    "restapiv4": [
        "WelcomePage_restapiv4HTML"
    ],
    "shell_guide": [
        "WelcomePage_shellGuideHTML",
        "WelcomePage_shellGuidePDF"
    ],
    "javasdk_guide": [
        "WelcomePage_javasdkGuideHTML",
        "WelcomePage_javasdkGuidePDF"
    ],
    "pythonsdk_guide": [
        "WelcomePage_pythonsdkGuideHTML",
        "WelcomePage_pythonsdkGuidePDF"
    ]
}

root_url = "{0}://{1}:{2}/{3}".format(
    scheme, vdc_host, vdc_port,
    OVIRT_ENGINE
)
