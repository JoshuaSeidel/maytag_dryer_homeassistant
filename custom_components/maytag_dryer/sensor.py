"""Sensor for maytag_dryer account status."""
from datetime import timedelta
import logging

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

CONF_USER = "user"
CONF_PASSWORD = "password"
CONF_DRYER_SAIDS = "dryersaids"
CONF_WASHER_SAIDS = "washersaids"
ICON_D = "mdi:tumble-dryer"
ICON_W = "mdi:washing-machine"
UNIT_STATES = {"0":"Ready",
               "1":"Not Running",
               "6":"Paused",
               "7":"Running",
               "8":"Wrinkle Prevent",
               "10":"Cycle Complete"
              }

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_USER): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_DRYER_SAIDS, default=[]): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(CONF_WASHER_SAIDS, default=[]): vol.All(cv.ensure_list, [cv.string]),
    }
)


BASE_INTERVAL = timedelta(minutes=2)
SCAN_INTERVAL = timedelta(minutes=2)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the maytag_dryer platform."""
    
    user = config.get(CONF_USER)
    password = config.get(CONF_PASSWORD)
    
    entitiesDryer = [maytag_dryerSensor(hass,user,password,said) for said in config.get(CONF_DRYER_SAIDS)]
    if entitiesDryer:
        async_add_entities(entitiesDryer, True)
    
    entitiesWasher = [maytag_washerSensor(hass,user,password,said) for said in config.get(CONF_WASHER_SAIDS)]
    if entitiesWasher:
        async_add_entities(entitiesWasher, True)
    
class maytag_dryerSensor(SensorEntity):
    """A class for the mealviewer account."""

    def __init__(self, hass, user, password,said):
        """Initialize the sensor."""
        self._name = "Dryer"
        self._user = user
        self._password = password
        self._said = said
        self._reauthorize = True
        self._access_token = None
        self._reauthCouter = 0
        self._state = "offline"
        self.hass = hass
        self._modelNumber = None
        self._applianceId = None
        self._lastSynced = None
        self._lastModified = None
        self._serialNumber = None
        self._doorOpen = None
        self._status = None
        self._cycleName = None
        self._cycleId = None
        self._manualDryTime = None
        self._drynessLevel = None
        self._airflow = None
        self._drying = None
        self._damp = None
        self._steaming = None
        self._sensing = None
        self._cooldown = None
        self._temperature = None
        self._operations = None
        self._powerOnHours = None
        self._hoursInUse = None
        self._totalCycles = None
        self._remoteEnabled = None
        self._timeRemaining = None
        self._online = None
        self._end_time = None
        
    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def entity_id(self):
        """Return the entity ID."""
        return 'sensor.maytag_dryer_' + (self._said).lower()

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"maytag_dryer_{self._said.lower()}"
        
    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._state
        
    @property
    def should_poll(self):
        """Turn off polling, will do ourselves."""
        return True
    
    async def authorize(self):
        """Update device state."""
        try:
            auth_url = "https://api.whrcloud.com/oauth/token"
            auth_header = {
                'content-type': 'application/x-www-form-urlencoded',
                'user-agent': 'okhttp/4.12.0',
            }
    
    
            auth_data = {
                'client_id': 'maytag_android_v1',
                'client_secret': 'f1XfYji_D9KfZGovyp8PMgRzrFKjhjY26TV0hu3Mt1-tCCNPl9s95z7QLUfB9UgB',
                'grant_type': 'password',
                'username': self._user,
                'password': self._password,
            }

            session = async_get_clientsession(self.hass)
            resp = await session.post(auth_url, data=auth_data, headers=auth_header)
            data = await resp.json()
            self._access_token = data.get('access_token')
            self._reauthCouter = 0
            self._reauthorize = False
            self._status = "Authorized"
 
        except Exception as err:
            _LOGGER.error("Dryer authorization failed: %s", err)
            self._access_token = None
            self._reauthCouter = self._reauthCouter + 1
            self._reauthorize = True
            self._status = "Authorization failed " + str(self._reauthCouter) + " times"
            self._state = "Authorization failed"

    async def async_update(self):
        """Update device state."""
        if self._reauthorize and self._reauthCouter < 5:
            await self.authorize()
        
        
        if self._access_token is not None:
            try:
                new_url = 'https://api.whrcloud.com/api/v1/appliance/' + self._said
                
                new_header = {
                    "Authorization": "bearer " + self._access_token,
                    'user-agent': 'okhttp/4.12.0',
                }
 
                session = async_get_clientsession(self.hass)
                resp = await session.get(new_url, headers=new_header)
                data = await resp.json()
                self._applianceId = data.get('applianceId')
                self._modelNumber = data.get('attributes').get('ModelNumber').get('value')
                self._lastSynced = data.get('lastFullSyncTime')
                self._lastModified = data.get('lastModified')
                self._serialNumber = data.get('attributes').get('XCat_ApplianceInfoSetSerialNumber').get('value')
                self._doorOpen = data.get('attributes').get('Cavity_OpStatusDoorOpen').get('value')
                self._status = data.get('attributes').get('Cavity_CycleStatusMachineState').get('value')
                self._cycleName = data.get('attributes').get('Cavity_CycleSetCycleName').get('value')
                self._cycleId = data.get('attributes').get('DryCavity_CycleSetCycleSelect').get('value')
                self._manualDryTime = data.get('attributes').get('DryCavity_CycleSetManualDryTime').get('value')
                self._drynessLevel = data.get('attributes').get('DryCavity_CycleSetDryness').get('value')
                self._airflow = data.get('attributes').get('DryCavity_CycleStatusAirFlowStatus').get('value')
                self._drying = data.get('attributes').get('DryCavity_CycleStatusDrying').get('value')        
                self._damp = data.get('attributes').get('DryCavity_CycleStatusDamp').get('value')                     
                self._steaming = data.get('attributes').get('DryCavity_CycleStatusSteaming').get('value')       
                self._sensing = data.get('attributes').get('DryCavity_CycleStatusSensing').get('value') 
                self._cooldown = data.get('attributes').get('DryCavity_CycleStatusCoolDown').get('value')     
                self._temperature = data.get('attributes').get('DryCavity_CycleSetTemperature').get('value')                    
                self._operations = data.get('attributes').get('Cavity_OpSetOperations').get('value')                      
                self._powerOnHours = data.get('attributes').get('XCat_OdometerStatusTotalHours').get('value')
                self._hoursInUse = data.get('attributes').get('XCat_OdometerStatusRunningHours').get('value')    
                self._totalCycles = data.get('attributes').get('XCat_OdometerStatusCycleCount').get('value')                     
                self._remoteEnabled = data.get('attributes').get('XCat_RemoteSetRemoteControlEnable').get('value')                    
                self._timeRemaining = data.get('attributes').get('Cavity_TimeStatusEstTimeRemaining').get('value')                  
                self._online = data.get('attributes').get('Online').get('value') 
                
                self._end_time = dt_util.now() + timedelta(seconds=int(self._timeRemaining))
                
                #status: [0=off, 1=on but not running, 7=running, 6=paused, 10=cycle complete]
                self._state =  UNIT_STATES.get(self._status,self._status)
                    
            except Exception as err:
                _LOGGER.error("Failed to update dryer state: %s", err)
                self._modelNumber = None
                self._applianceId = None
                self._lastSynced = None
                self._lastModified = None
                self._serialNumber = None
                self._doorOpen = None
                self._status = "Data Update Failed"
                self._state = "Data Update Failed"
                self._cycleName = None
                self._cycleId = None
                self._manualDryTime = None
                self._drynessLevel = None
                self._airflow = None
                self._drying = None
                self._damp = None        
                self._steaming = None     
                self._sensing = None
                self._cooldown = None
                self._temperature = None                  
                self._operations = None               
                self._powerOnHours = None
                self._hoursInUse = None    
                self._totalCycles = None
                self._remoteEnabled = None
                self._timeRemaining = None           
                self._online = None
                self._reauthorize = True
                self._end_time = None
        else: # No token... try again!
            self._reauthorize = True


    
    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attr = {}
        
        attr["modelNumber"] = self._modelNumber
        attr["applianceid"]= self._applianceId
        attr["lastsynced"]= self._lastSynced 
        attr["lastmodified"]= self._lastModified 
        attr["dooropen"]= self._doorOpen 
        attr["status"]= self._status 
        attr["cyclename"]= self._cycleName 
        attr["cycleid"]= self._cycleId 
        attr["manualdrytime"]= self._manualDryTime 
        attr["drynesslevel"]= self._drynessLevel
        attr["airflow"]= self._airflow
        attr["drying"]= self._drying 
        attr["damp"]= self._damp         
        attr["steaming"]= self._steaming      
        attr["sensing"]= self._sensing 
        attr["cooldown"]= self._cooldown 
        attr["temperature"]= self._temperature                   
        attr["operations"]= self._operations                
        attr["poweronhours"]= self._powerOnHours 
        attr["hoursinuse"]= self._hoursInUse     
        attr["totalcycles"]= self._totalCycles 
        attr["remoteenabled"]= self._remoteEnabled 
        attr["timeremaining"]= self._timeRemaining            
        attr["online"]= self._online 
        attr["end_time"]= self._end_time 
        attr["reauth_cnt"]= self._reauthCouter

        return attr

    
    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return ICON_D


class maytag_washerSensor(SensorEntity):
    
    """A class for the mealviewer account."""

    def __init__(self, hass, user, password,said):
        """Initialize the sensor."""
        self._name = "washer"
        self._user = user
        self._password = password
        self._said = said
        self._reauthorize = True
        self._access_token = None
        self._reauthCouter = 0
        self._state = "offline"
        self._updateCounter = 0
        self.hass = hass
        self._applianceId = None
        self._modelNumber = None
        self._lastSynced = None
        self._lastModified = None
        self._serialNumber = None
        self._doorOpen = None
        self._doorLocked = None
        self._drawerOpen = None
        self._status = None
        self._cycleName = None
        self._cycleId = None
        self._needClean = None
        self._delayTime = None
        self._delayRemaining = None
        self._rinsing = None
        self._draining = None
        self._filling = None
        self._spinning = None
        self._soaking = None
        self._sensing = None
        self._washing = None
        self._addGarmet = None
        self._temperature = None
        self._operations = None
        self._powerOnHours = None
        self._hoursInUse = None
        self._totalCycles = None
        self._remoteEnabled = None
        self._timeRemaining = None
        self._spinSpeed = None
        self._soilLevel = None
        self._online = None
        self._end_time = None
        self._dispense1Enable = None
        self._dispense1Level = None
        self._dispense1Concentration = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def entity_id(self):
        """Return the entity ID."""
        
        return 'sensor.maytag_washer_' + (self._said).lower()

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"maytag_washer_{self._said.lower()}"
        
    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._state
        
    @property
    def should_poll(self):
        """Turn off polling, will do ourselves."""
        return True
    
    async def authorize(self):
        """Update device state."""
        try:
            auth_url = "https://api.whrcloud.com/oauth/token"

            auth_header = {
                'content-type': 'application/x-www-form-urlencoded',
                'user-agent': 'okhttp/4.12.0',
            }
    
    
            auth_data = {
                'client_id': 'maytag_android_v1',
                'client_secret': 'f1XfYji_D9KfZGovyp8PMgRzrFKjhjY26TV0hu3Mt1-tCCNPl9s95z7QLUfB9UgB',
                'grant_type': 'password',
                'username': self._user,
                'password': self._password,
            }
            
            
            session = async_get_clientsession(self.hass)
            resp = await session.post(auth_url, data=auth_data, headers=auth_header)
            data = await resp.json()

            self._access_token = data.get('access_token')
            self._reauthCouter = 0
            self._reauthorize = False
            
        except Exception as err:
            _LOGGER.error("Washer authorization failed: %s", err)
            self._access_token = None
            self._reauthCouter = self._reauthCouter + 1
            self._reauthorize = True
            self._status = "Authorization failed " + str(self._reauthCouter) + " times"
            self._state = "Authorization failed"
        
    async def async_update(self):
        """Update device state."""
        if self._reauthorize and self._reauthCouter < 5:
            await self.authorize()
        
        if self._access_token is not None:
            try:
                new_url = 'https://api.whrcloud.com/api/v1/appliance/' + self._said

                new_header = {
                    "Authorization": "bearer " + self._access_token,
                    'user-agent': 'okhttp/4.12.0',
                }
 
                session = async_get_clientsession(self.hass)
                resp = await session.get(new_url, headers=new_header)
                data = await resp.json()
                _LOGGER.debug(data)
                self._applianceId = data.get('applianceId')
                self._modelNumber = data.get('attributes').get('ModelNumber').get('value')
                self._lastSynced = data.get('lastFullSyncTime')
                self._lastModified = data.get('lastModified')
                self._serialNumber = data.get('attributes').get('XCat_ApplianceInfoSetSerialNumber').get('value')
                self._doorOpen = data.get('attributes').get('Cavity_OpStatusDoorOpen').get('value')
                self._doorLocked = data.get('attributes').get('Cavity_OpStatusDoorLocked').get('value')
                self._drawerOpen = data.get('attributes').get('WashCavity_OpStatusDispenserDrawerOpen', {}).get('value')
                self._status = data.get('attributes').get('Cavity_CycleStatusMachineState').get('value')
                self._cycleName = data.get('attributes').get('Cavity_CycleSetCycleName').get('value')
                self._cycleId = data.get('attributes').get('WashCavity_CycleSetCycleSelect').get('value')
                self._needClean = data.get('attributes').get('WashCavity_CycleStatusCleanReminder').get('value')
                self._delayTime = data.get('attributes').get('Cavity_TimeSetDelayTime').get('value')
                self._delayRemaining = data.get('attributes').get('Cavity_TimeStatusDelayTimeRemaining').get('value')
                self._rinsing = data.get('attributes').get('WashCavity_CycleStatusRinsing').get('value')
                self._draining = data.get('attributes').get('WashCavity_CycleStatusDraining').get('value')
                self._filling = data.get('attributes').get('WashCavity_CycleStatusFilling').get('value')
                self._spinning = data.get('attributes').get('WashCavity_CycleStatusSpinning').get('value')
                self._soaking = data.get('attributes').get('WashCavity_CycleStatusSoaking').get('value')
                self._sensing = data.get('attributes').get('WashCavity_CycleStatusSensing').get('value')
                self._washing = data.get('attributes').get('WashCavity_CycleStatusWashing').get('value')
                self._addGarmet = data.get('attributes').get('WashCavity_CycleStatusAddGarment').get('value')
                self._temperature = data.get('attributes').get('WashCavity_CycleSetTemperature').get('value')                    
                self._operations = data.get('attributes').get('Cavity_OpSetOperations').get('value')                      
                self._powerOnHours = data.get('attributes').get('XCat_OdometerStatusTotalHours').get('value')
                self._hoursInUse = data.get('attributes').get('XCat_OdometerStatusRunningHours').get('value')    
                self._totalCycles = data.get('attributes').get('XCat_OdometerStatusCycleCount').get('value')                     
                self._remoteEnabled = data.get('attributes').get('XCat_RemoteSetRemoteControlEnable').get('value')
                
              
                self._dispense1Enable = data.get('attributes').get('WashCavity_CycleSetBulkDispense1Enable', {}).get('value')
                self._dispense1Level = data.get('attributes').get('WashCavity_OpStatusBulkDispense1Level', {}).get('value')
                self._dispense1Concentration = data.get('attributes').get('WashCavity_OpSetBulkDispense1Concentration', {}).get('value')
                
                self._timeRemaining = data.get('attributes').get('Cavity_TimeStatusEstTimeRemaining').get('value') 
                self._spinSpeed = data.get('attributes').get('WashCavity_CycleSetSpinSpeed').get('value') 
                self._soilLevel = data.get('attributes').get('WashCavity_CycleSetSoilLevel').get('value') 
                self._online = data.get('attributes').get('Online').get('value') 
                self._end_time = dt_util.now() + timedelta(seconds=int(self._timeRemaining))
                #status: [0=off, 1=on but not running, 7=running, 6=paused, 10=cycle complete]

                self._state = UNIT_STATES.get(self._status,self._status)                 
                self._updateCounter = self._updateCounter + 1
                    
            except Exception as err:
                _LOGGER.error("Failed to update washer state: %s", err)
                
                self._status = "Data Update Failed"
                self._state = "Data Update Failed" 
                self._applianceId = None
                self._modelNumber = None
                self._lastSynced = None
                self._lastModified = None
                self._serialNumber = None
                self._doorOpen = None
                self._doorLocked = None
                self._drawerOpen = None
                
                self._cycleName = None
                self._cycleId = None
                self._needClean = None
                self._delayTime = None
                self._delayRemaining = None
                self._rinsing = None
                self._draining = None
                self._filling = None
                self._spinning = None
                self._soaking = None
                self._sensing = None
                self._washing = None
                self._addGarmet = None
                self._temperature = None                    
                self._operations = None                      
                self._powerOnHours = None
                self._hoursInUse = None    
                self._totalCycles = None                     
                self._remoteEnabled = None                    
                self._timeRemaining = None
                self._spinSpeed = None 
                self._soilLevel = None 
                self._online = None
                self._end_time = None
                
                self._dispense1Enable = None
                self._dispense1Level = None
                self._dispense1Concentration = None
                
                self._reauthorize = True
        else: # No token... try again!
            self._reauthorize = True



    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attr = {}
        
        attr["applianceid"]= self._applianceId
        attr["modelNumber"] = self._modelNumber
        attr["lastsynced"] = self._lastSynced
        attr["lastmodified"] = self._lastModified
        attr["serialnumber"] = self._serialNumber
        attr["dooropen"] = self._doorOpen
        attr["doorlocked"] = self._doorLocked
        attr["draweropen"] = self._drawerOpen
                
        attr["cyclename"] = self._cycleName
        attr["cycleid"] = self._cycleId
        attr["needclean"] = self._needClean
        attr["delaytime"] = self._delayTime
        attr["delayremaining"] = self._delayRemaining
        attr["rinsing"] = self._rinsing
        attr["draining"] = self._draining
        attr["filling"] = self._filling
        attr["spinning"] = self._spinning
        attr["soaking"] = self._soaking
        attr["sensing"] = self._sensing
        attr["washing"] = self._washing
        attr["addgarmet"] = self._addGarmet
        attr["temperature"] = self._temperature                    
        attr["operations"] = self._operations                      
        attr["oweronhours"] = self._powerOnHours
        attr["hoursinuse"] = self._hoursInUse    
        attr["totalcycles"] = self._totalCycles                     
        attr["remoteenabled"] = self._remoteEnabled                    
        attr["timeremaining"] = self._timeRemaining
        attr["spinspeed"] = self._spinSpeed 
        attr["soillevel"] = self._soilLevel 
        attr["online"] = self._online
        attr["end_time"] = self._end_time
        attr["status"] = self._status
        attr["auth_cnt"]= self._reauthCouter
        attr["update_count"]= self._updateCounter
        
        attr["dispense_concentration"] = self._dispense1Concentration
        attr["dispense_enable"] = self._dispense1Enable 
        attr["dispense_level"]  = self._dispense1Level
        
  
        return attr

    
    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return ICON_W
