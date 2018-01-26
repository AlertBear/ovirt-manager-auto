from art.test_handler.settings import ART_CONFIG as art_config

parameters = art_config['PARAMETERS']
rest_connection = art_config['REST_CONNECTION']
enums = art_config['elements_conf']['RHEVM Enums']

vdc_host = rest_connection['host']
vdc_port = rest_connection['port']
scheme = rest_connection.get('scheme')
product = parameters['product_name']

upstream_flag = 'ovirt' in product.lower()

OVIRT_ENGINE = 'ovirt-engine'

DOC_LINK_IDS = [
    'WelcomePage_releaseNotesHTML',
    'WelcomePage_releaseNotesPDF',
    'WelcomePage_technicalNotesHTML',
    'WelcomePage_technicalNotesPDF',
    'WelcomePage_packageManifestHTML',
    'WelcomePage_packageManifestPDF',
    'WelcomePage_planningHTML',
    'WelcomePage_planningPDF',
    'WelcomePage_disasterHTML',
    'WelcomePage_disasterPDF',
    'WelcomePage_installationGuideHTML',
    'WelcomePage_installationGuidePDF',
    'WelcomePage_selfhosted_installationGuideHTML',
    'WelcomePage_selfhosted_installationGuidePDF',
    'WelcomePage_upgradeGuideHTML',
    'WelcomePage_upgradeGuidePDF',
    'WelcomePage_intro_adminGuideHtml',
    'WelcomePage_intro_adminGuidePDF',
    'WelcomePage_adminGuideHtml',
    'WelcomePage_adminGuidePDF',
    'WelcomePage_dwhGuideHtml',
    'WelcomePage_dwhGuidePDF',
    'WelcomePage_userportalGuideHTML',
    'WelcomePage_userportalGuidePDF',
    'WelcomePage_vmGuideHTML',
    'WelcomePage_vmGuidePDF',
    'WelcomPage_technical_referenceHTML',
    'WelcomePage_technical_referencePDF',
    'WelcomePage_restapiHTML',
    'WelcomePage_restapiPDF',
    'WelcomePage_restapiv4HTML',
    'WelcomePage_shellGuideHTML',
    'WelcomePage_shellGuidePDF',
    'WelcomePage_javasdkGuideHTML',
    'WelcomePage_javasdkGuidePDF',
    'WelcomePage_pythonsdkGuideHTML',
    'WelcomePage_pythonsdkGuidePDF'
]

root_url = '{0}://{1}:{2}/{3}'.format(
    scheme, vdc_host, vdc_port, OVIRT_ENGINE
)
