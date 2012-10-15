

PARAMETERS = 'PARAMETERS'
DC_TYPE = 'data_center_type'

def get_vds_section(config):
    vds_section = PARAMETERS
    dc_val = config[PARAMETERS][DC_TYPE].upper()
    if dc_val != 'NONE' and dc_val in conf:
        vds_section = dc_val
    return vds_section

