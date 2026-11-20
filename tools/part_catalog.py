"""Orderable candidates for quoting; availability remains a supplier check."""

def apply(parts):
    resistor_codes={'10K':'10KL','10k':'10KL','1K':'1KL','1k':'1KL',
        '5.1K':'5K1L','5.1k':'5K1L','4.7k':'4K7L','10':'10RL',
        '200':'200RL','27 ohm':'27RL','47k':'47KL','100k':'100KL'}
    caps={
        ('0.1uF','0402'): 'GRM155R71C104KA88D',
        ('1uF','0402'): 'GRM155R61A105KE15D',
        ('2.2uF','0402'): 'GRM155R61A225KE01D',
        ('15pF','0402'): 'GRM1555C1H150JA01D',
        ('100nF','0603'): 'GRM188R71H104KA93D',
        ('22pF','0603'): 'GRM1885C1H220JA01D',
        ('1uF','0603'): 'GRM188R61A105KA61D',
        ('10uF','0603'): 'GRM188R60J106ME47D',
        ('10uF_0603','0603'): 'GRM188R60J106ME47D',
        ('10uF','0805'): 'GRM21BR61A106KE19L',
    }
    exact={
        'U4':('Raspberry Pi','SC1509-A4'),
        'Q3':('Diodes Incorporated','DMP2045UFY4-7'),
        'L1':('TDK','DFE252012F-3R3M=P2'),
        'D1':('Lite-On','LTST-C190KRKT'),
        'D2':('Lite-On','LTST-C190KFKT'),
        'D4':('Nexperia','PMEG2020AEA,115'),
        'D5':('OPSCO','SK6805-EC15'),
        'SW1':('C&K / Littelfuse','KMR221GLFS'),
        'SW2':('C&K / Littelfuse','KMR221GLFS'),
        'U1':('Winbond','W25Q64JVXGIQ'),
        'U2':('Richtek','RT9080-33GJ5'),
        'U3':('Microchip','MCP73831T-2ACI/OT'),
        'U5':('CEVA','BNO085'), 'U6':('Bosch Sensortec','BMP581'),
        'U7':('Texas Instruments','TPS22919DCKR'),
        'Y1':('Abracon','ABM8-272-T3'), 'Y2':('Abracon','ABS07-32.768KHZ-T'),
        'JBAT1':('JST','S2B-PH-SM4-TB(LF)(SN)'),
        'JQT1':('JST','SM04B-SRSS-TB(LF)(SN)'),
        'JTAG1':('JST','BM02B-SRSS-TB(LF)(SN)'),
        'JUSB1':('GCT','USB4110-GF-A'),
        'JSD1':('Molex','1040310811'),
        'JSERVO1':('Samtec','TSW-104-08-T-T-RA'),
    }
    for ref,p in parts.items():
        package=p['package']
        size=next((s for s in ('0402','0603','0805') if s in package),None)
        if ref.startswith('R'):
            p['manufacturer']='Yageo'
            p['mpn']='RC'+size+'FR-07'+resistor_codes[p['value']]
        elif ref.startswith('C'):
            p['manufacturer']='Murata'
            p['mpn']=caps[(p['value'],size)]
        if ref in exact:p['manufacturer'],p['mpn']=exact[ref]
    parts['Q3']['value']='DMP2045UFY4'
    # The inherited RGB part is specified above the regulated 3.3-V supply.
    # Retain its optional footprint; omit it from the quoted populated build.
    # The ordinary status and charging LEDs remain populated.
    parts['D5']['dnp']=True
    parts['D5']['procurement_note']='DNP: RGB supply rating is not guaranteed at 3.3 V'

