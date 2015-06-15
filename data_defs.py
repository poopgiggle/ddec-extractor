import struct
from utils import bit_at_index
import sys
import string

try:
    # Try from django's slugify first
    from django.utils.text import slugify as django_slugify
    slugify = lambda slug: re.sub('[-]', '_', django_slugify(slug))
except ImportError:
    # Then use awesome-slugify
    from slugify import Slugify
    slugify = Slugify(to_lower=True, separator='_')


def parse_message(message):
    num_pages = ord(message[2])
    index = 4
    pages = []
    for i in range(num_pages):
        page_type = ord(message[index])
        page_size_plus_bitmask = struct.unpack('<H',message[index+2:index+4])[0]
        bitmask_len = ord(message[index+4])
        bitmask_bytes = message[index+5:index+5+bitmask_len]
        this_page = request_codes[page_type](bitmask_bytes)
        page_size = page_size_plus_bitmask - bitmask_len - 1
        try:
            assert(page_size % len(this_page) == 0)
        except:
            print("Expected some multiple of %d, got %d" % (page_size,len(this_page)))
            sys.exit()
        page_index = 0
        for i in range(page_size / len(this_page)):
            base_index = index+5+bitmask_len+page_index
            pages.append(this_page.get_data(message[base_index:base_index+len(this_page)]))
            page_index += len(this_page)

        index += 4+page_size_plus_bitmask

    return pages
        



class Parameter():
    __allowed = ('format','name','scale','units','repeat')

    format = 'B'
    name = 'Default Name'
    scale = 1
    units = 'Units'
    repeat = 1
    _data = None
    _bytes = None

    def __init__(self,*args,**kwargs):
        for k,v in kwargs.iteritems():
            assert(k in self.__class__.__allowed)
            setattr(self,k,v)

    def __len__(self):
        try:
            return struct.calcsize(self.format)*self.repeat
        except:
            print("format error in class %s. format is: %s" % (self.__class__.__name__,self.format))
            sys.exit()

    def get_data(self,byte_list):
        assert(len(byte_list) == len(self))
        try:
            this_data = map(lambda x: x*self.scale,struct.unpack(self.format*self.repeat,byte_list))
        except:
            print("Format: %s, Byte_list: %s, Class: %s" % (self.format*self.repeat,repr(byte_list),self.__class__.__name__))
        if len(this_data) == 1:
            this_data = this_data[0]
        self._data = this_data
        self._bytes = byte_list
        return this_data

    @property
    def data(self):
        if not self._data or not self._bytes:
            return None
        value_data = {
            'name':self.name
            'units':self.units
            'bytes':self._bytes
            }
        if len(self._data) == 1:
            value_data.update({'value':repr(self._data)})
        else:
            value_data.update({'values':map(repr,self._data)})

        return self.slug_name : value_data
            

    @property
    def slug_name(self):
        if self._slug_name:
            return self._slug_name
        else:
            self._slug_name = slugify(unicode(self.name))
            return self._slug_name

class SubPage():
   __allowed = ('param_list','repeat')
   repeat = 1
   def __init__(self,*args,**kwargs):
       for k,v in kwargs.iteritems():
           assert(k in self.__class__.__allowed)
           setattr(self,k,v)
           
   def __len__(self):
       return sum(map(len,self.param_list)) * self.repeat

   def get_data(self,byte_list):
       index = 0
       data_elts = []
       for i in range(self.repeat):
           params = []
           for param in self.param_list:
               param_data = param.get_data(byte_list[index:index+len(param)])
               params.append(param_data)
               index += len(param)
           if len(params) == 1:
               data_elts.append(params[0])
           else:
               data_elts.append(params)

       return data_elts


class DataPage(object):
    subpages = []
    def __init__(self,bitmask):
        bitmask_bytes = struct.unpack('B'*len(bitmask),bitmask)
        self.pages_to_render = []
        for i in range(len(bitmask_bytes)):
            for j in range(8):
                if 8 * i + j < len(self.subpages) and bit_at_index(bitmask_bytes[i],j):
                    self.pages_to_render.append(self.subpages[8 * i + j])

    def __len__(self):
        return sum(map(len,self.pages_to_render))

    def get_data(self,byte_list):
        index = 0
        data_elts = []
        for subpage in self.pages_to_render:
            page_data = subpage.get_data(byte_list[index:index+len(subpage)])
            if len(page_data) == 1:
                data_elts.append(page_data[0])
            else:
                data_elts.append(page_data)
            index += len(subpage)

        return data_elts
            



class LongParameter(Parameter):
    format = "I"

class ShortParameter(Parameter):
    format = "H"

class StringParameter():
    length = 10
    def __len__(self):
        return self.length

    def get_data(self,byte_list):
        try:
            assert(len(byte_list) == len(self))
        except AssertionError:
            print("StringParameter needed byte string of length %d, got length %d" % (len(self),len(byte_list)))
        return ''.join(x for x in byte_list if x in string.printable)

##############################
# Incident data parameters   #
##############################

class EngineHours(LongParameter):
    name = "Engine Hours"
    scale = .05
    units = "Hours"

class Odometer(LongParameter):
    name = "Incident Odometer"
    scale = 0.1
    units = "Miles"

class RoadSpeed(Parameter):
    name = "Road Speed"
    scale = 0.5
    units = "MPH"

class EngineSpeed(ShortParameter):
    name = "Engine Speed"
    scale = 0.25
    units = "RPM"

class PercentLoad(Parameter):
    name = "Engine Load"
    scale = 0.5
    units = "% load"

class PercentThrottle(Parameter):
    name = "Throttle"
    scale = 0.4
    units = "% throttle"

class CruiseMode(Parameter):
    name = "Cruise Mode"

class SampleCount(Parameter):
    name = "Valid Sample Count"
    units = "Samples"

class Timestamp(LongParameter):
    name = "Timestamp"

class IncidentTimestamp(Timestamp):
    name = "Incident Timestamp"

#############################
# Trip parameters           #
#############################

class TripDistance(Odometer):
    name = "Trip Distance"

class TripFuel(LongParameter):
    scale = 0.125
    name = "Trip Fuel"
    units = "Gallons"

class TripTime(LongParameter):
    name = "Trip Time"
    units = "Seconds"

class DriveDistance(Odometer):
    name = "Drive Distance"

class DriveFuel(TripFuel):
    name = "Drive Fuel"

class DriveTime(TripTime):
    name = "Drive Time"

class CruiseDistance(Odometer):
    name = "Cruise Distance"

class CruiseFuel(TripFuel):
    name = "Cruise Fuel"

class CruiseTime(TripTime):
    name = "Cruise Time"

class TopGearDistance(Odometer):
    name = "Top Gear Distance"

class TopGearFuel(TripFuel):
    name = "Top Gear Fuel"

class TopGearTime(TripTime):
    name = "Top Gear Time"

class IdleFuel(TripFuel):
    name = "Idle Fuel"

class IdleTime(TripTime):
    name = "Idle Time"

class VSGPTOFuel(TripFuel):
    name = "VSG (PTO) Fuel"

class VSGPTOTime(TripTime):
    name = "VSG (PTO) Time"

class VSGPTOIdleFuel(TripFuel):
    name = "VSG (PTO) Idle Fuel"
    
class VSGPTOIdleTime(TripTime):
    name = "VSG (PTO) Idle Time"

class OverSpeedATime(TripTime):
    name = "Overspeed A Time"

class OverSpeedBTime(TripTime):
    name = "Overspeed B Time"

class OverRevTime(TripTime):
    name = "Over Rev Time"
    
class CoastTime(TripTime):
    name = "Coast Time"

class PeakRoadSpeed(RoadSpeed):
    name = "Peak Road Speed"

class PeakEngineSpeed(EngineSpeed):
    name = "Peak Engine Speed"

class InterruptNumber(ShortParameter):
    name = "Number of Power Interrupts"
    units = "Count"

class InterruptHours(EngineHours):
    name = "Engine Hours of Last Interrupt"

class InterruptDuration(LongParameter):
    name = "Duration of Last Interrupt"
    scale = 4
    units = "Minutes"

class TimeoutCount(ShortParameter):
    name = "Number of J1587 Timeouts"
    units = "Count"

class TimeoutHours(EngineHours):
    name = "Engine Hours of Last Timeout"

class TimeoutDuration(LongParameter):
    name = "Duration of Last Timeout"
    units = "Seconds"

class DriveLoadAccumulation(LongParameter):
    name = "Drive Engine Load Accumulation"
    scale = 0.5
    units = "Sum %load / sec"

class HardBrakeCount(ShortParameter):
    name = "Hard Brake Count"
    units = "Count"

class DriverIncidentCount(ShortParameter):
    name = "Driver Incident Count"
    units = "Count"

class FutureHardBrakeIndex(Parameter):
    name = "Index for Future Hard Brake in Queue"
    units = "Index"

class FutureDriverIncidentIndex(Parameter):
    name = "Index for Future Driver Incident in Queue"
    units = "Index"

class TripArmedTime(LongParameter):
    name = "Trip Armed Time"
    units = "Seconds"

class TripRunTime(LongParameter):
    name = "Trip Run Time"
    units = "Seconds"

class StartOptimisedIdleFuelValue(ShortParameter):
    name = "Start Optimized Idle Fuel Value"
    scale = 0.25
    units = "Gallons"

class TripIdleTimeSaved(LongParameter):
    name = "Trip Idle Time Saved"
    units = "Minutes"

class TotalIdleTimeSaved(LongParameter):
    name = "Total Idle Time Saved"
    units = "Minutes"

class TripIdleFuelSaved(ShortParameter):
    name = "Trip Idle Fuel Saved"
    scale = 0.25
    units = "Gallons"

class TotalIdleFuelSaved(ShortParameter):
    name = "Total Idle Fuel Saved"
    scale = 0.25
    units = "Gallons"

class TotalArmedTime(LongParameter):
    name = "Total Armed Time"
    units = "Seconds"

class TotalRunTime(LongParameter):
    name = "Total Run Time"
    units = "Seconds"

class BatteryTime(LongParameter):
    name = "Battery Time"
    units = "Seconds"

class TopGearRatio(Parameter):
    name = "Top Gear Ratio"
    units = "RPM/MPH"

class TopGearTimeStamp(LongParameter):
    name = "Top Gear Time Stamp"
    units = "Timestamp"

class TopGear1Distance(LongParameter):
    name = "Top Gear 1 Distance"
    scale = 0.1
    units = "Miles"

class TopGear1Fuel(LongParameter):
    name = "Top Gear 1 Fuel"
    scale = 0.125
    units = "Gallons"

class TopGear1Time(LongParameter):
    name = "Top Gear 1 Time"
    units = "Seconds"

class TopGear1Ratio(Parameter):
    name = "Top Gear 1 Ratio"
    units = "RPM/MPH"

class TopGear1TimeStamp(LongParameter):
    name = "Top Gear 1 Time Stamp"
    units = "Timestamp"

class TopGearCruiseDistance(LongParameter):
    name = "Top Gear Cruise Distance"
    scale = 0.1
    units = "Miles"

class TopGearCruiseFuel(LongParameter):
    name = "Top Gear Cruise Fuel"
    scale = 0.125
    units = "Gallons"

class TopGearCruiseTime(LongParameter):
    name = "Top Gear Cruise Time"
    units = "Seconds"

class RSGDistance(LongParameter):
    name = "RSG Distance"
    scale = 0.1
    units = "Miles"

class RSGFuel(LongParameter):
    name = "RSG Fuel"
    scale = 0.125
    units = "Gallons"

class RSGTime(LongParameter):
    name = "RSG Time"
    units = "Seconds"

class StopIdleFuel(LongParameter):
    name = "Stop Idle Fuel"
    scale = 0.125
    units = "Gallons"

class StopIdleTime(LongParameter):
    name = "Stop Idle Time"
    units = "Seconds"

class PumpDistance(LongParameter):
    name = "Pump Distance"
    scale = 0.1
    units = "Miles"

class PumpFuel(LongParameter):
    name = "Pump Fuel"
    scale = 0.125
    units = "Gallons"

class PumpTime(LongParameter):
    name = "Pump Time"
    units = "Seconds"

class JakeBrakeTime(LongParameter):
    name = "Jake Brake Time"
    units = "Seconds"

class FanTimeEngine(LongParameter):
    name = "Fan Time (Engine)"
    units = "Seconds"

class FanTimeManual(FanTimeEngine):
    name = "Fan Time (Manual)"

class FanTimeAirConditioning(FanTimeEngine):
    name = "Fan Time (AC)"

class FanTimeDPF(FanTimeEngine):
    name = "Fan Time (DPF)"

class OptimisedIdleArmedTime(LongParameter):
    name = "Armed Time"
    units = "Seconds"

class OptimisedIdleRunTime(LongParameter):
    name = "Run Time"
    units = "Seconds"

class OptimisedIdleBatteryTime2(LongParameter):
    name = "Battery Time 2"
    units = "Seconds"

class OptimisedIdleEngineTempTime(LongParameter):
    name = "Engine Temp. Time"
    units = "Seconds"

class OptimisedIdleThermostatTime(LongParameter):
    name = "Thermostat Time"
    units = "Seconds"

class OptimisedIdleExtendedIdleTime(LongParameter):
    name = "Extended Idle Time"
    units = "Seconds"

class OptimisedIdleContinuousTime(LongParameter):
    name = "Contiuous Time"
    units = "Seconds"
    
class PeakRoadSpeedTimeStamp(LongParameter):
    name = "Peak Road Speed Time Stamp"
    units = "Timestamp"

class PeakEngineRPMTimeStamp(LongParameter):
    name = "Peak Engine RPM Time Stamp"
    units = "Timestamp"

class TripStartTimeStamp(LongParameter):
    name = "Trip Start Time Stamp"
    units = "Timestamp"

class TripStartOdometer(LongParameter):
    name = "Trip Start Odometer"
    units = "Miles"

class CountOverSpeedACount(ShortParameter):
    name = "Over Speed A Count"
    units = "Count"

class CountOverSpeedBCount(ShortParameter):
    name = "Over Speed B Count"
    units = "Count"

class CountOverRevCount(ShortParameter):
    name = "Over Rev Count"
    units = "Count"

class CountBrakeCount(LongParameter):
    name = "Brake Count"
    units = "Count"

class CountHardBrakeCount(ShortParameter):
    name = "Hard Brake Count 2"
    units = "Count"

class CountFirmBrakeCount(ShortParameter):
    name = "Firm Brake Count"
    units = "Count"

class BVEBrakingVelocityEnergy(LongParameter):
    name = "Braking Velocity Energy"
    units = "Sum energy"

class BVECrankshaftRevolutions(LongParameter):
    name = "Crank Shaft Revolutions"
    units = "Revolutions"

class AlertCount(ShortParameter):
    name = "Alert Count"
    units = "Count"

class DriveAverageLoadFactor(Parameter):
    name = "Drive Average Load Factor"
    units = "% max load"

class OICBatteryStartsNormal(ShortParameter):
    name = "Battery starts - normal"
    units = "Count"

class OICBatteryStartsAlternative(ShortParameter):
    name = "Battery starts - alternative"
    units = "Count"

class OICBatteryStartsContinuousRun(ShortParameter):
    name = "Battery starts - continuous run"
    units = "Count"

class DPFRSParkedRegenAttempts(ShortParameter):
    name = "Parked DPF regeneration attempts"
    units = "Count"

class DPFRSDrivingRegenAttempts(ShortParameter):
    name = "Driving DPF regeneration attempts"
    units = "Count"

class DPFRSParkedRegenCompletions(ShortParameter):
    name = "Parked DPF regeneration completions"
    units = "Count"

class DPFRSDrivingRegenCompletions(ShortParameter):
    name = "Driving DPF regeneration completions"
    units = "Count"

class DPFRSParkedDPFFuelVolume(LongParameter):
    name = "Parked DPF Fuel Volume"
    scale = 0.0004882813
    units = "Gallons"

class DPFRSAutomaticDPFFuelVolume(DPFRSParkedDPFFuelVolume):
    name = "Automatic DPF Fuel Volume"

class DPFRSRegenerationTime(LongParameter):
    name = "DPF Regeneration Time"
    units = "Timestamp"

class PCCDistance(LongParameter):
    name = "Predictive Cruise Distance"
    scale = 0.1
    units = "Miles"

class PCCFuel(LongParameter):
    name = "Predictive Cruise Fuel"
    scale = 0.00048828125
    units = "Gallons"

class PCCTime(LongParameter):
    name = "Predictive Cruise Time"
    units = "Seconds"
    

##############################
# TripTable Parameters       #
##############################

class BrakeCounts(LongParameter):
    name = "Brake Counts for Speed Bands"
    repeat = 10

class HBCHardBrakeCounts(ShortParameter):
    name = "Hard Brake Counts for Speed Bands"
    repeat = 10

class HBCFirmBrakeCounts(ShortParameter):
    name = "Firm Brake Counts for Speed Bands"
    repeat = 10

class TIRSERBTimeInSpeedBandsRPMBand1(LongParameter):
    name = "Time in Speed Bands when in RPM Band 1"
    repeat = 10

class TIRSERBTimeInSpeedBandsRPMBand2(LongParameter):
    name = "Time in Speed Bands when in RPM Band 2"
    repeat = 10

class TIRSERBTimeInSpeedBandsRPMBand3(LongParameter):
    name = "Time in Speed Bands when in RPM Band 3"
    repeat = 10

class TIRSERBTimeInSpeedBandsRPMBand4(LongParameter):
    name = "Time in Speed Bands when in RPM Band 4"
    repeat = 10

class TIRSERBTimeInSpeedBandsRPMBand5(LongParameter):
    name = "Time in Speed Bands when in RPM Band 5"
    repeat = 10

class TIRSERBTimeInSpeedBandsRPMBand6(LongParameter):
    name = "Time in Speed Bands when in RPM Band 6"
    repeat = 10

class TIRSERBTimeInSpeedBandsRPMBand7(LongParameter):
    name = "Time in Speed Bands when in RPM Band 7"
    repeat = 10

class TIRSERBTimeInSpeedBandsRPMBand8(LongParameter):
    name = "Time in Speed Bands when in RPM Band 8"
    repeat = 10

class TIRSERBTimeInSpeedBandsRPMBand9(LongParameter):
    name = "Time in Speed Bands when in RPM Band 9"
    repeat = 10

class TIRSERBTimeInSpeedBandsOverRev(LongParameter):
    name = "Time in Speed Bands when in Over Rev"
    repeat = 10

class TIELRBRPMBand1(LongParameter):
    name = "Time in Load Bands when in RPM Band 1"
    repeat = 10

class TIELRBRPMBand2(LongParameter):
    name = "Time in Load Bands when in RPM Band 2"
    repeat = 10

class TIELRBRPMBand3(LongParameter):
    name = "Time in Load Bands when in RPM Band 3"
    repeat = 10

class TIELRBRPMBand4(LongParameter):
    name = "Time in Load Bands when in RPM Band 4"
    repeat = 10

class TIELRBRPMBand5(LongParameter):
    name = "Time in Load Bands when in RPM Band 5"
    repeat = 10

class TIELRBRPMBand6(LongParameter):
    name = "Time in Load Bands when in RPM Band 6"
    repeat = 10

class TIELRBRPMBand7(LongParameter):
    name = "Time in Load Bands when in RPM Band 7"
    repeat = 10

class TIELRBRPMBand8(LongParameter):
    name = "Time in Load Bands when in RPM Band 8"
    repeat = 10

class TIELRBRPMBand9(LongParameter):
    name = "Time in Load Bands when in RPM Band 9"
    repeat = 10

class TIELRBOverRev(LongParameter):
    name = "Time in Load Bands when in Over Rev"
    repeat = 10

class TimeInAutomaticOverSpeedBands(LongParameter):
    name = "Time in Automatic Over Speed Bands"
    repeat = 10

class TimeInAutomaticEngineOverRevBands(LongParameter):
    name = "Time in Automatic Engine Over Rev Bands"
    repeat = 10

################################
# ConfigurationData Parameters #
################################

class FleetIdleGoalPercentage(Parameter):
    name = "Fleet Idle Goal Percentage"
    units = "% max fleet idle goal"

class FuelEconomyGoal(ShortParameter):
    name = "Fuel Economy Goal"
    scale = 0.01
    units = "MPG"

class OverRevLimitA(ShortParameter):
    name = "Over Rev Limit A"
    scale = 0.25
    units = "RPM"

class OverSpeedALimit(Parameter):
    name = "Over Speed A Limit"
    units = "MPH"

class OverSpeedBLimit(Parameter):
    name = "Over Speed B Limit"
    units = "MPH"

class Password(StringParameter):
    name = "Password"
    length = 6

class DriverIdentifier(StringParameter):
    name = "Driver Identifier"
    length = 10

class VehicleIdentifier(StringParameter):
    name = "Vehicle Identifier"
    length = 10

class CurrentOdometer(Odometer):
    name = "Current Odometer"

class HardBrakeDecelLimit(Parameter):
    name = "Hard Brake Deceleration Limit"
    units = "MPH/S"

class IdleTimeLimitStop(Parameter):
    name = "Idle Time Limit (Stop)"
    units = "Minutes"

class AlarmState(Parameter):
    name = "Alarm State"

class DayIntensity(Parameter):
    name = "Day Intensity"

class NightIntensity(Parameter):
    name = "Night Intensity"

class Units(Parameter):
    name = "Units"

class Language(Parameter):
    name = "Language"

class DataHubDeviceMID(Parameter):#value is an enum
    name = "Data Hub Device MID"

class DataEntryRangeType(Parameter):#enum
    name = "Data Entry Range Type"

class AccessType(Parameter):#enum
    name = "Acess Type"

class PromptedDriverID(Parameter):#enum
    name = "Prompted Driver ID"

class MPGAdjustment(Parameter):
    name = "MPG Adjustment"
    scale = 0.01

class SoftwareVersion(StringParameter):
    name = "Software Version"
    length = 5

class ECMType(Parameter):#enum
    name = "ECM Type"
    units = "mph"

class SpeedBandLimit1(Parameter):
    name = "Speed Band 1 Limit"
    units = "mph"

class SpeedBandLimit2(Parameter):
    name = "SpeedBand 2 Limit"
    units = "mph"

class SpeedBandLimit3(Parameter):
    name = "SpeedBand 3 Limit"
    units = "mph"

class SpeedBandLimit4(Parameter):
    name = "SpeedBand 4 Limit"
    units = "mph"

class SpeedBandLimit5(Parameter):
    name = "SpeedBand 5 Limit"
    units = "mph"

class SpeedBandLimit6(Parameter):
    name = "SpeedBand 6 Limit"
    units = "mph"

class SpeedBandLimit7(Parameter):
    name = "SpeedBand 7 Limit"
    units = "mph"

class SpeedBandLimitA(Parameter):
    name = "SpeedBand A Limit"
    units = "mph"

class SpeedBandLimitB(Parameter):
    name = "SpeedBand B Limit"
    units = "mph"

class RPMBandLimit1(Parameter):
    name = "RPM Band 1 Limit"
    units = "RPM"

class RPMBandLimit2(Parameter):
    name = "RPM Band 2 Limit"
    units = "RPM"

class RPMBandLimit3(Parameter):
    name = "RPM Band 3 Limit"
    units = "RPM"

class RPMBandLimit4(Parameter):
    name = "RPM Band 4 Limit"
    units = "RPM"

class RPMBandLimit5(Parameter):
    name = "RPM Band 5 Limit"
    units = "RPM"

class RPMBandLimit6(Parameter):
    name = "RPM Band 6 Limit"
    units = "RPM"

class RPMBandLimit7(Parameter):
    name = "RPM Band 7 Limit"
    units = "RPM"

class RPMBandLimit8(Parameter):
    name = "RPM Band 8 Limit"
    units = "RPM"

class RPMBandLimitOverRev(Parameter):
    name = "Over Rev Limit"
    units = "RPM"

class LoadBandLimit(Parameter):
    scale = 0.5
    units = "% load"

class LoadBandLimit1(LoadBandLimit):
    name = "Load Band 1 Limit"

class LoadBandLimit2(LoadBandLimit):
    name = "Load Band 2 Limit"

class LoadBandLimit3(LoadBandLimit):
    name = "Load Band 3 Limit"

class LoadBandLimit4(LoadBandLimit):
    name = "Load Band 4 Limit"

class LoadBandLimit5(LoadBandLimit):
    name = "Load Band 5 Limit"

class LoadBandLimit6(LoadBandLimit):
    name = "Load Band 6 Limit"

class LoadBandLimit7(LoadBandLimit):
    name = "Load Band 7 Limit"

class LoadBandLimit8(LoadBandLimit):
    name = "Load Band 8 Limit"

class LoadBandLimit9(LoadBandLimit):
    name = "Load Band 9 Limit"

class TrendSampleInterval(ShortParameter):
    name = "Trend Sample Interval"
    scale = 0.05
    units = "Engine Hours"

class RPMIdleThreshold(ShortParameter):
    name = "RPM Idle Threshold"
    scale = 0.25
    units = "RPM"

class LoadIdleThreshold(Parameter):
    name = "Load Idle Threshold"
    scale = 0.5
    units = "% load"

class ServiceDueFlag(Parameter):#enum
    name = "Service Due Flag"

class ConfigurationPageChangeTimestamp(LongParameter):
    name = "Configuration Page Change Timestamp"

class ConfigurationChecksum(ShortParameter):
    name = "Configuration Checksum"

class IdleAlgorithm(Parameter):#enum
    name = "Idle Algorithm"

class TimeZone(Parameter):
    name = "Timezone"
    scale = 0.25
    units = "Hours"

class TripResetLockOut(Parameter):#enum
    name = "Trip Reset Lock Out"
    
class OilPressureMinRPMLimit(Parameter):
    name = "Oil Pressure Minimum RPM Limit"
    scale = 50
    units = "RPM"

class OilPressureMaxRPMLimit(OilPressureMinRPMLimit):
    name = "Oil Pressure Maximum RPM Limit"

class OilPressureMinTempLimit(Parameter):
    name = "Oil Pressure Minimum Temp Limit"
    scale = 5
    units = "Degrees F"

class OilPressureMaxTempLimit(OilPressureMinTempLimit):
    name = "Oil Pressure Maximum Temp Limit"

class BoostPressureMinimumRPMLimit(Parameter):
    name = "Boost Pressure Minimum RPM Limit"
    scale = 5
    units = "RPM"

class BoostPressureMaximumRPMLimit(BoostPressureMinimumRPMLimit):
    name = "Boost Pressure Maximum RPM Limit"

class BoostPressureMinimumLoadLimit(Parameter):
    name = "Boost Pressure Minimum Load Limit"
    units = "% load"

class BoostPressureMaximumLoadLimit(BoostPressureMinimumLoadLimit):
    name = "Boost Pressure Maximum Load Limit"

class BatteryVoltageMinimumRPMLimit(Parameter):
    name = "Battery Voltage Minimum RPM Limit"
    scale = 50
    units = "RPM"

class BatteryVoltageMaximumRPMLimit(BatteryVoltageMinimumRPMLimit):
    name = "Battery Voltage Maximum RPM Limit"

class ServiceAlertPercentage(Parameter):
    name = "Service Alert Percentage"
    units = "% limit"

class LastStopIncidentEnable(Parameter):#enum
    name = "Last Stop Incident Enable"

class DriverCardEnable(Parameter):#enum
    name = "Driver Card Enable"

class ButtonFeedbackEnable(Parameter):#enum
    name = "Button Feedback Enable"
    
class OverspeedAEnable(Parameter):#enum
    name = "Overspeed A Enable"

class OverspeedBEnable(Parameter):#enum
    name = "Overspeed B Enable"

class OverRevEnable(Parameter):#enum
    name = "Over Rev Enable"

class CPCSoftwareVersionID(StringParameter):
    name = "CPC Software Version ID"
    length = 70

class PTOIdleRPMThreshold(ShortParameter):
    name = "PTO Idle RPM Threshold"
    scale = 0.25
    units = "RPM"

class PTOIdleLoadRPMThreshold(Parameter):
    name = "PTO Idle Load RPM Threshold"
    scale = 0.5
    units = "% load"

class FirmBrakeDecelerationLimit(Parameter):
    name = "Firm Brake Deceleration Limit"
    units =  "mph/s"


###################################
# DetailedAlert Parameters         #
###################################

class AlertCode(Parameter):#enum
    name = "Alert Code"
    
class AlertTimeStamp(LongParameter):
    name = "Alert Timestamp"

class AlertRoadSpeed(Parameter):
    name = "Alert Road Speed"
    scale = 0.5
    units = "MPH"

class AlertEngineRPM(ShortParameter):
    name = "Alert Engine RPM"
    scale = 0.25
    units = "RPM"

class AlertTurboBoostPressure(ShortParameter):
    name = "Alert Turbo Boost Pressure"
    scale = 0.125
    units = "PSI"

class AlertOilPressure(ShortParameter):
    name = "Alert Oil Pressure"
    scale = 0.125
    units = "PSI"

class AlertFuelPressure(ShortParameter):
    name = "Alert Fuel Pressure"
    scale = 0.125
    units = "PSI"

class AlertAirIntakeTemp(ShortParameter):
    name = "Alert Air Intake Temp"
    scale = 0.25
    units = "degrees F"

class AlertCoolantTemp(AlertAirIntakeTemp):
    name = "Alert Coolant Temp"

class AlertOilTemp(AlertAirIntakeTemp):
    name = "Alert Oil Temp"

class AlertFuelTemp(AlertAirIntakeTemp):
    name = "Alert Fuel Temp"

class AlertThrottlePercent(Parameter):
    name = "Alert Throttle Percent"
    scale = 0.4
    units = "% throttle"

class AlertPulseWidth(ShortParameter):
    name = "Alert Pulse Width"
    scale = 0.01
    units = "degrees"

class AlertBrakeState(Parameter):
    name = "Alert Brake State"

class AlertEngineLoad(Parameter):
    name = "Alert Engine Load"
    scale = 0.5
    units = "% load"

class AlertCruiseMode(Parameter):
    name = "Alert Cruise Mode"

###############################
# EngineUsage parameters      #
###############################

class DailyDistanceTravelled(ShortParameter):
    name = "Daily Distance Travelled"
    scale = 0.1
    units = "Miles"

class DailyFuelConsumption(ShortParameter):
    name = "Daily Fuel Consumption"
    scale = 0.25
    units = "Gallons"

class StartDayTimeStamp(LongParameter):
    name = "Start of Day Time Stamp"
    
class StartDayOdometer(LongParameter):
    name = "Start of Day Odometer"
    scale = 0.1
    units = "Miles"

class IdleTimeBreakdown(Parameter):#ALERT
    format = "<LLL"
    name = "Idle Time Breakdown"
    
class DriveTimeBreakdown(Parameter):#ALERT
    format = "<LLL"
    name = "Drive Time Breakdown"


###################################
# PermanentData Parameters        #
###################################

class PermanentTotalDistance(LongParameter):
    name = "Total Distance"
    scale = 0.1
    units = "Miles"

class PermanentTotalFuel(LongParameter):
    name = "Total Fuel"
    scale = 0.125
    units = "Gallons"

class PermanentTotalTime(LongParameter):
    name = "Total Time"
    units = "Seconds"

class PermanentTotalIdleFuel(LongParameter):
    name = "Total Idle Fuel"
    scale = 0.125
    units = "Gallons"

class PermanentTotalIdleTime(LongParameter):
    name = "Total Idle Time"
    units = "Seconds"

class PermanentTotalVSGFuel(LongParameter):
    name = "Total VSG Fuel"
    scale = 0.125
    units = "gallons"

class PermanentTotalVSGTime(LongParameter):
    name = "Total VSG Time"
    units = "Seconds"

class PermanentVSGPTOIdleFuel(LongParameter):
    name = "VSG (PTO) Idle Fuel"
    scale = 0.125
    units = "Gallons"

class PermanentVSGPTOIdleTime(LongParameter):
    name = "VSG (PTO) Idle Time"
    units = "Seconds"

class PermanentTotalCruiseTime(LongParameter):
    name = "Total Cruise Time"
    units = "Seconds"

class PermanentOptimizedIdleActiveTime(LongParameter):
    name = "Optimized Idle Active Time"
    units = "Seconds"

class PermanentOptimizedIdleRunTime(LongParameter):
    name = "Optimized Idle Run Time"
    units = "Seconds"

class PermanentEngineBrakeTime(LongParameter):
    name = "Engine Brake Time"
    units = "Seconds"

class PermanentDriveAverageLoadFactor(Parameter):
    name = "Drive Average Load Factor"
    units = "%"

class PermanentEngineRevolutions(LongParameter):
    name = "Engine Revolutions"
    scale = 1000
    units = "revolutions"

class PermanentFanTimeEngine(LongParameter):
    name = "Fan Time (Engine)"
    units = "Seconds"

class PermanentFanTimeManual(LongParameter):
    name = "Fan Time (Manual)"
    units = "Seconds"

class PermanentFanTimeAC(LongParameter):
    name = "Fan Time (AC)"
    units = "Seconds"

class PermanentFanTimeDPF(LongParameter):
    name = "Fan Time (DPF)"
    units = "Seconds"

class PermanentPeakRoadSpeed(Parameter):
    name = "Peak Road Speed"
    scale = 0.5
    units = "MPH"

class PermanentPeakEngineRPM(ShortParameter):
    name = "Peak Engine RPM"
    scale = 0.25
    units = "RPM"

class PermanentPeakRoadSpeedTimeStamp(LongParameter):
    name = "Peak Road Speed Time Stamp"

class PermanentPeakEngineRPMTimeStamp(LongParameter):
    name = "Peak Engine RPM Time Stamp"
    

class PermanentTotalBatteryStartsNormal(ShortParameter):
    name = "Total Battery Starts - Normal"

class PermanentTotalBatteryStartsAlternative(ShortParameter):
    name = "Total Battery Starts - Alternative"

class PermanentTotalBatteryStartsContinuous(ShortParameter):
    name = "Total Battery Starts - Continuous Run"

class PermanentParkedDPFRegenAttempts(LongParameter):
    name = "Parked DPF Regen Attempts Count"

class PermanentDrivingDPFRegenAttempts(LongParameter):
    name = "Driving DPF Regen Attempts Count"

class PermanentParkedDPFRegenComplete(LongParameter):
    name = "Parked DPF Regen Complete Count"

class PermanentDrivingDPFRegenComplete(LongParameter):
    name = "Driving DPF Regen Complete Count"

class PermanentLastParkedDPFRegenTimeStamp(LongParameter):
    name = "Last Parked DPF Regen Time Stamp"

class PermanentLastDrivingDPFRegenTimeStamp(LongParameter):
    name = "Last Driving DPF Regen Time Stamp"

class PermanentParkedDPFFuelVolume(LongParameter):
    name = "Parked DPF Fuel Volume"
    scale = 0.00048828125
    units = "Gallons"

class PermanentDrivingDPFFuelVolume(LongParameter):
    name = "Driving DPF Fuel Volume"
    scale = 0.00048828125
    units = "Gallons"

class PermanentParkedTime(LongParameter):
    name = "Parked Time"
    units = "Seconds"

class PermanentTotalPredictiveCruiseTime(LongParameter):
    name = "Total Predictive Cruise (PCC) Time"
    units = "Seconds"


##############################
# Header Parameters          #
##############################

class HeaderEngineHours(LongParameter):
    name = "Current Engine Hours"
    scale = 0.05
    units = "Hours"

class HeaderDriverID(StringParameter):
    name = "Current Driver ID"
    length = 10

class HeaderVehicleID(StringParameter):
    name = "Vehicle ID"
    length = 10

class HeaderExtractionOdometer(LongParameter):
    name = "Extraction Time Odometer"
    scale = 0.1
    units = "Miles"

class HeaderExtractionTimeStamp(LongParameter):
    name = "Extraction Time Time Stamp"
    
class HeaderConfigurationChecksum(ShortParameter):
    name = "Configuration Checksum"
    
class HeaderEngineSerialNumber(StringParameter):
    name = "Engine Serial Number"
    length = 10

class HeaderStatusInformation(Parameter):
    name = "Status Information"

class HeaderMBESerialNumber(StringParameter):
    name = "MBE Engine Serial Number"
    length = 14

class HeaderSoftwareMajorVersion(ShortParameter):
    name = "Major Version"

class HeaderSoftwareMinorVersion(ShortParameter):
    name = "Minor Version"




###########################
# Incident Subpages       #
###########################

class IncidentSubPage(SubPage):
    param_list = [RoadSpeed(),
                  EngineSpeed(),
                  PercentLoad(),
                  PercentThrottle(),
                  CruiseMode()]

class LastStopPage(IncidentSubPage):
    repeat = 120

class HardBrakePage(IncidentSubPage):
    repeat = 75


############################
# Trip Subpages            #
############################

class TripSubPage(SubPage):
    param_list = [TripDistance(),
                  TripFuel(),
                  TripTime()]

class DriveSubPage(SubPage):
    param_list = [DriveDistance(),
                  DriveFuel(),
                  DriveTime()]

class CruiseSubPage(SubPage):
    param_list = [CruiseDistance(),
                  CruiseFuel(),
                  CruiseTime()]

class TopGearSubPage(SubPage):
    param_list = [TopGearDistance(),
                  TopGearFuel(),
                  TopGearTime()]

class IdleSubPage(SubPage):
    param_list = [IdleFuel(),
                  IdleTime()]

class VSGPTOSubPage(SubPage):
    param_list = [VSGPTOFuel(),
                  VSGPTOTime(),
                  VSGPTOIdleFuel(),
                  VSGPTOIdleTime()]

class OverSpeedATimeSubPage(SubPage):
    param_list = [OverSpeedATime()]

class OverSpeedBTimeSubPage(SubPage):
    param_list = [OverSpeedBTime()]

class OverRevTimeSubPage(SubPage):
    param_list = [OverRevTime()]

class CoastTimeSubPage(SubPage):
    param_list = [CoastTime()]

class PeakSubPage(SubPage):
    param_list = [PeakRoadSpeed(),
                  PeakEngineSpeed()]

class InterruptSubPage(SubPage):
    param_list = [InterruptNumber(),
                  InterruptHours(),
                  InterruptDuration()]

class TimeoutSubPage(SubPage):
    param_list = [TimeoutCount(),
                  TimeoutHours(),
                  TimeoutDuration()]

class DriveLoadAccumulationSubPage(SubPage):
    param_list = [DriveLoadAccumulation()]

class HardBrakeCountSubPage(SubPage):
    param_list = [HardBrakeCount(),
                  DriverIncidentCount(),
                  FutureHardBrakeIndex(),
                  FutureDriverIncidentIndex()]

class OptimisedIdleData1SubPage(SubPage):
    param_list = [TripArmedTime(),
                  TripRunTime(),
                  StartOptimisedIdleFuelValue(),
                  TripIdleTimeSaved(),
                  TripIdleFuelSaved(),
                  TotalIdleFuelSaved(),
                  TotalArmedTime(),
                  TotalRunTime(),
                  BatteryTime()]

class TopGearRatioSubPage(SubPage):
    param_list = [TopGearRatio()]

class TopGearTimeStampSubPage(SubPage):
    param_list = [TopGearTimeStamp()]

class TopGear1DistanceSubPage(SubPage):
    param_list = [TopGear1Distance(),
                  TopGear1Fuel(),
                  TopGear1Time()]

class TopGear1RatioSubPage(SubPage):
    param_list = [TopGear1Ratio(),
                  TopGear1TimeStamp()]

class TopGearCruiseSubPage(SubPage):
    param_list = [TopGearCruiseDistance(),
                  TopGearCruiseFuel(),
                  TopGearCruiseTime()]

class RSGSubPage(SubPage):
    param_list = [RSGDistance(),
                  RSGFuel(),
                  RSGTime()]

class StopIdleSubPage(SubPage):
    param_list = [StopIdleFuel(),
                  StopIdleTime()]

class PumpSubPage(SubPage):
    param_list = [PumpDistance(),
                  PumpFuel(),
                  PumpTime()]

class JakeBrakeTimeSubPage(SubPage):
    param_list = [JakeBrakeTime()]

class FanTimeSubPage(SubPage):
    param_list = [FanTimeEngine(),
                  FanTimeManual(),
                  FanTimeAirConditioning(),
                  FanTimeDPF()]

class OptimisedIdleData2SubPage(SubPage):
    param_list = [OptimisedIdleArmedTime(),
                  OptimisedIdleRunTime(),
                  OptimisedIdleBatteryTime2(),
                  OptimisedIdleEngineTempTime(),
                  OptimisedIdleThermostatTime(),
                  OptimisedIdleExtendedIdleTime(),
                  OptimisedIdleContinuousTime()]

class PeakTimeStampSubPage(SubPage):
    param_list = [PeakRoadSpeedTimeStamp(),
                  PeakEngineRPMTimeStamp()]

class TripStartSubPage(SubPage):
    param_list = [TripStartTimeStamp(),
                  TripStartOdometer()]


class CountsSubPage(SubPage):
    param_list = [CountOverSpeedACount(),
                  CountOverSpeedBCount(),
                  CountOverRevCount(),
                  CountBrakeCount(),
                  CountHardBrakeCount(),
                  CountFirmBrakeCount()]

class BVESubPage(SubPage):
    param_list = [BVEBrakingVelocityEnergy(),
                  BVECrankshaftRevolutions()]

class AlertCountSubPage(SubPage):
    param_list = [AlertCount()]

class DriveAverageLoadFactorSubPage(SubPage):
    param_list = [DriveAverageLoadFactor()]

class OptimizedIdleCountsSubPage(SubPage):
    param_list = [OICBatteryStartsNormal(),
                  OICBatteryStartsAlternative(),
                  OICBatteryStartsContinuousRun()]

class DPFRegenerationStatisticsSubPage(SubPage):
    param_list = [DPFRSParkedRegenAttempts(),
                  DPFRSDrivingRegenAttempts(),
                  DPFRSParkedRegenCompletions(),
                  DPFRSDrivingRegenCompletions(),
                  DPFRSParkedDPFFuelVolume(),
                  DPFRSAutomaticDPFFuelVolume(),
                  DPFRSRegenerationTime()]

class PredictiveCruiseSubPage(SubPage):
    param_list = [PCCDistance(),
                  PCCFuel(),
                  PCCTime()]
                  
                  
######################
# TripTable subpages #
######################

class BrakeCountsSubPage(SubPage):
    param_list = [BrakeCounts()]

class HardBrakeCountsSubPage(SubPage):
    param_list = [HBCHardBrakeCounts(),
                  HBCFirmBrakeCounts()]

class TimeInRoadSpeedEngineRPMBandsSubPage(SubPage):
    param_list = [TIRSERBTimeInSpeedBandsRPMBand1(),
                  TIRSERBTimeInSpeedBandsRPMBand2(),
                  TIRSERBTimeInSpeedBandsRPMBand3(),
                  TIRSERBTimeInSpeedBandsRPMBand4(),
                  TIRSERBTimeInSpeedBandsRPMBand5(),
                  TIRSERBTimeInSpeedBandsRPMBand6(),
                  TIRSERBTimeInSpeedBandsRPMBand7(),
                  TIRSERBTimeInSpeedBandsRPMBand8(),
                  TIRSERBTimeInSpeedBandsRPMBand9(),
                  TIRSERBTimeInSpeedBandsOverRev()]

class TimeInEngineLoadEngineRPMBandsSubPage(SubPage):
    param_list = [TIELRBRPMBand1(),
                  TIELRBRPMBand2(),
                  TIELRBRPMBand3(),
                  TIELRBRPMBand4(),
                  TIELRBRPMBand5(),
                  TIELRBRPMBand6(),
                  TIELRBRPMBand7(),
                  TIELRBRPMBand8(),
                  TIELRBRPMBand9(),
                  TIELRBOverRev()]

class TimeInAutomaticOverSpeedBandsSubPage(SubPage):
    param_list = [TimeInAutomaticOverSpeedBands()]

class TimeInAutomaticEngineOverRevBandsSubPage(SubPage):
    param_list = [TimeInAutomaticEngineOverRevBands()]

#################################
# ConfigurationData SubPages    #
#################################

class FleetIdleGoalPercentageSubPage(SubPage):
    param_list = [FleetIdleGoalPercentage()]

class FuelEconomyGoalSubPage(SubPage):
    param_list = [FuelEconomyGoal()]

class OverRevLimitASubPage(SubPage):
    param_list = [OverRevLimitA()]

class OverSpeedLimitSubPage(SubPage):
    param_list = [OverSpeedALimit(),
                  OverSpeedBLimit()]

class PasswordSubPage(SubPage):
    param_list = [Password()]

class DriverIDSubPage(SubPage):
    param_list = [DriverIdentifier()]

class VehicleIDSubPage(SubPage):
    param_list = [VehicleIdentifier()]

class CurrentOdometerSubPage(SubPage):
    param_list = [CurrentOdometer()]

class HardBrakeDecelLimitSubPage(SubPage):
    param_list = [HardBrakeDecelLimit()]

class IdleTimeLimitStopSubPage(SubPage):
    param_list = [IdleTimeLimitStop()]

class AlarmStateSubPage(SubPage):
    param_list = [AlarmState()]

class IntensitySubPage(SubPage):
    param_list = [DayIntensity(),
                  NightIntensity()]

class UnitsSubPage(SubPage):
    param_list = [Units()]

class LanguageSubPage(SubPage):
    param_list = [Language()]

#reuse TopGearRatioSubPage

class DataHubDeviceMIDSubPage(SubPage):
    param_list = [DataHubDeviceMID()]

class DataEntryRangeTypeSubPage(SubPage):
    param_list = [DataEntryRangeType()]

class AccessTypeSubPage(SubPage):
    param_list = [AccessType()]

class PromptedDriverIDSubPage(SubPage):
    param_list = [PromptedDriverID()]

class MPGAdjustmentSubPage(SubPage):
    param_list = [MPGAdjustment()]

class SoftwareVersionSubPage(SubPage):
    param_list = [SoftwareVersion()]

class ECMTypeSubPage(SubPage):
    param_list = [ECMType()]

class SpeedBandLimitsSubPage(SubPage):
    param_list = [SpeedBandLimit1(),
                  SpeedBandLimit2(),
                  SpeedBandLimit3(),
                  SpeedBandLimit4(),
                  SpeedBandLimit5(),
                  SpeedBandLimit6(),
                  SpeedBandLimit7(),
                  SpeedBandLimitA(),
                  SpeedBandLimitB()]

class RPMBandLimitsSubPage(SubPage):
    param_list = [RPMBandLimit1(),
                  RPMBandLimit2(),
                  RPMBandLimit3(),
                  RPMBandLimit4(),
                  RPMBandLimit5(),
                  RPMBandLimit6(),
                  RPMBandLimit7(),
                  RPMBandLimit8(),
                  RPMBandLimitOverRev()]


class LoadBandLimitsSubPage(SubPage):
    param_list = [LoadBandLimit1(),
                  LoadBandLimit2(),
                  LoadBandLimit3(),
                  LoadBandLimit4(),
                  LoadBandLimit5(),
                  LoadBandLimit6(),
                  LoadBandLimit7(),
                  LoadBandLimit8(),
                  LoadBandLimit9()]

class TrendSampleIntervalSubPage(SubPage):
    param_list = [TrendSampleInterval()]

class RPMIdleThresholdSubPage(SubPage):
    param_list = [RPMIdleThreshold()]

class LoadIdleThresholdSubPage(SubPage):
    param_list = [LoadIdleThreshold()]

class TopGear1RatioSubPage2(SubPage):
    param_list = [TopGear1Ratio()]

class ServiceDueFlagSubPage(SubPage):
    param_list = [ServiceDueFlag()]

class ConfigurationPageChangeTimestampDataPage(SubPage):
    param_list = [ConfigurationPageChangeTimestamp()]

class ConfigurationPageChecksumSubPage(SubPage):
    param_list = [ConfigurationChecksum()]

class IdleAlgorithmSubPage(SubPage):
    param_list = [IdleAlgorithm()]

class TimeZoneSubPage(SubPage):
    param_list = [TimeZone()]

class TripResetLockOutSubPage(SubPage):
    param_list = [TripResetLockOut()]

class TrendConfigurationSubPage(SubPage):
    param_list = [OilPressureMinRPMLimit(),
                  OilPressureMaxRPMLimit(),
                  OilPressureMinTempLimit(),
                  OilPressureMaxTempLimit(),
                  BoostPressureMinimumRPMLimit(),
                  BoostPressureMaximumRPMLimit(),
                  BoostPressureMinimumLoadLimit(),
                  BoostPressureMaximumLoadLimit(),
                  BatteryVoltageMinimumRPMLimit(),
                  BatteryVoltageMaximumRPMLimit()]

class ServiceAlertPercentageSubPage(SubPage):
    param_list = [ServiceAlertPercentage()]

class LastStopIncidentEnableSubPage(SubPage):
    param_list = [LastStopIncidentEnable()]

class DriverCardEnableSubPage(SubPage):
    param_list = [DriverCardEnable()]

class ButtonFeedbackEnableSubPage(SubPage):
    param_list = [ButtonFeedbackEnable()]

class OverspeedAEnableSubPage(SubPage):
    param_list = [OverspeedAEnable()]

class OverspeedBEnableSubPage(SubPage):
    param_list = [OverspeedBEnable()]

class OverRevEnableSubPage(SubPage):
    param_list = [OverRevEnable()]

class CPCSoftwareVersionIDSubPage(SubPage):
    param_list = [CPCSoftwareVersionID()]

class PTOIdleRPMThresholdSubPage(SubPage):
    param_list = [PTOIdleRPMThreshold(),
                  PTOIdleLoadRPMThreshold()]

class FirmBrakeDecelerationLimitSubPage(SubPage):
    param_list = [FirmBrakeDecelerationLimit()]

###########################
# DetailedAlert Subpages  #
###########################

class AlertCodeSubPage(SubPage):
    param_list = [AlertCode()]

class AlertTimeStampSubPage(SubPage):
    param_list = [AlertTimeStamp()]

class AlertRoadSpeedSubPage(SubPage):
    repeat = 12
    param_list = [AlertRoadSpeed(),
                  AlertEngineRPM(),
                  AlertTurboBoostPressure(),
                  AlertOilPressure(),
                  AlertFuelPressure(),
                  AlertAirIntakeTemp(),
                  AlertCoolantTemp(),
                  AlertOilTemp(),
                  AlertFuelTemp(),
                  AlertThrottlePercent(),
                  AlertPulseWidth(),
                  AlertBrakeState(),
                  AlertEngineLoad(),
                  AlertCruiseMode()]


#############################
# EngineUsage Subpages      #
#############################

class DailySubPage(SubPage):
    param_list = [DailyDistanceTravelled(),
                  DailyFuelConsumption(),
                  StartDayTimeStamp(),
                  StartDayOdometer()]

class BreakdownSubPage(SubPage):
    param_list = [IdleTimeBreakdown(),
                  DriveTimeBreakdown()]



#############################
# PermanentData Subpages    #
#############################

class PermanentDataSubPage(SubPage):
    param_list = [PermanentTotalDistance(),
                  PermanentTotalFuel(),
                  PermanentTotalTime()]

class PermanentTotalIdleSubPage(SubPage):
    param_list = [PermanentTotalIdleFuel(),
                  PermanentTotalIdleTime()]

class PermanentTotalVSGSubPage(SubPage):
    param_list = [PermanentTotalVSGFuel(),
                  PermanentTotalVSGTime(),
                  PermanentVSGPTOIdleFuel(),
                  PermanentVSGPTOIdleTime()]

class PermanentTotalCruiseTimeSubPage(SubPage):
    param_list = [PermanentTotalCruiseTime()]

class PermanentOptimizedIdleSubPage(SubPage):
    param_list = [PermanentOptimizedIdleActiveTime(),
                  PermanentOptimizedIdleRunTime()]

class PermanentEngineBrakeTimeSubPage(SubPage):
    param_list = [PermanentEngineBrakeTime()]

class PermanentDriveAverageLoadFactorSubPage(SubPage):
    param_list = [PermanentDriveAverageLoadFactor()]

class PermanentEngineRevolutionsSubPage(SubPage):
    param_list = [PermanentEngineRevolutions()]

class PermanentFanTimeSubPage(SubPage):
    param_list = [PermanentFanTimeEngine(),
                  PermanentFanTimeManual(),
                  PermanentFanTimeAC(),
                  PermanentFanTimeDPF()]

class PermanentPeakSubPage(SubPage):
    param_list = [PermanentPeakRoadSpeed(),
                  PermanentPeakEngineRPM(),
                  PermanentPeakRoadSpeedTimeStamp(),
                  PermanentPeakEngineRPMTimeStamp()]

class PermanentOptimizedIdleCountsSubPage(SubPage):
    param_list = [PermanentTotalBatteryStartsNormal(),
                  PermanentTotalBatteryStartsAlternative(),
                  PermanentTotalBatteryStartsContinuous()]

class PermanentDPFRegenStatisticsSubPage(SubPage):
    param_list = [PermanentParkedDPFRegenAttempts(),
                  PermanentDrivingDPFRegenAttempts(),
                  PermanentParkedDPFRegenComplete(),
                  PermanentDrivingDPFRegenComplete(),
                  PermanentLastParkedDPFRegenTimeStamp(),
                  PermanentLastDrivingDPFRegenTimeStamp(),
                  PermanentParkedDPFFuelVolume(),
                  PermanentDrivingDPFFuelVolume(),
                  PermanentParkedTime()]

class PermanentTotalPredictiveCruiseTimeSubPage(SubPage):
    param_list = [PermanentTotalPredictiveCruiseTime()]



############################
# Header subpages          #
############################

class HeaderEngineHoursSubPage(SubPage):
    param_list = [HeaderEngineHours()]

class HeaderDriverIDSubPage(SubPage):
    param_list = [HeaderDriverID()]

class HeaderVehicleIDSubPage(SubPage):
    param_list = [HeaderVehicleID()]

class HeaderExtractionOdometerSubPage(SubPage):
    param_list = [HeaderExtractionOdometer()]

class HeaderExtractionTimeStampSubPage(SubPage):
    param_list = [HeaderExtractionTimeStamp()]

class HeaderConfigurationChecksumSubPage(SubPage):
    param_list = [HeaderConfigurationChecksum()]

class HeaderEngineSerialNumberSubPage(SubPage):
    param_list = [HeaderEngineSerialNumber()]

class HeaderStatusInformationSubPage(SubPage):
    param_list = [HeaderStatusInformation()]

class HeaderMBESerialNumberSubPage(SubPage):
    param_list = [HeaderMBESerialNumber()]

class HeaderSoftwareVersionSubPage(SubPage):
    param_list = [HeaderSoftwareMajorVersion(),
                  HeaderSoftwareMinorVersion()]





######################
# Full datapages     #
######################

class Header(DataPage):
    subpages = [HeaderEngineHoursSubPage(),
                HeaderDriverIDSubPage(),
                HeaderVehicleIDSubPage(),
                HeaderExtractionOdometerSubPage(),
                HeaderExtractionTimeStampSubPage(),
                HeaderConfigurationChecksumSubPage(),
                HeaderEngineSerialNumberSubPage(),
                HeaderStatusInformationSubPage(),
                HeaderMBESerialNumberSubPage(),
                HeaderSoftwareVersionSubPage()]


class EngineUsage(DataPage):
    subpages = [DailySubPage(),
               BreakdownSubPage()]

class DetailedAlert(DataPage):
    subpages = [AlertCodeSubPage(),
                AlertTimeStampSubPage(),
                AlertRoadSpeedSubPage()]

class ConfigurationData(DataPage):
    subpages = [FleetIdleGoalPercentageSubPage(),
                FuelEconomyGoalSubPage(),
                OverRevLimitASubPage(),
                OverSpeedLimitSubPage(),
                PasswordSubPage(),
                DriverIDSubPage(),
                VehicleIDSubPage(),
                CurrentOdometerSubPage(),
                HardBrakeDecelLimitSubPage(),
                IdleTimeLimitStopSubPage(),
                AlarmStateSubPage(),
                IntensitySubPage(),
                UnitsSubPage(),
                LanguageSubPage(),
                TopGearRatioSubPage(),
                DataHubDeviceMIDSubPage(),
                DataEntryRangeTypeSubPage(),
                AccessTypeSubPage(),
                PromptedDriverIDSubPage(),
                MPGAdjustmentSubPage(),
                SoftwareVersionSubPage(),
                ECMTypeSubPage(),
                SpeedBandLimitsSubPage(),
                RPMBandLimitsSubPage(),
                LoadBandLimitsSubPage(),
                TrendSampleIntervalSubPage(),
                RPMIdleThresholdSubPage(),
                LoadIdleThresholdSubPage(),
                TopGear1RatioSubPage2(),
                ServiceDueFlagSubPage(),
                ConfigurationPageChangeTimestampDataPage(),
                ConfigurationPageChecksumSubPage(),
                IdleAlgorithmSubPage(),
                TimeZoneSubPage(),
                TripResetLockOutSubPage(),
                TrendConfigurationSubPage(),
                ServiceAlertPercentageSubPage(),
                LastStopIncidentEnableSubPage(),
                DriverCardEnableSubPage(),
                ButtonFeedbackEnableSubPage(),
                OverspeedAEnableSubPage(),
                OverspeedBEnableSubPage(),
                OverRevEnableSubPage(),
                CPCSoftwareVersionIDSubPage(),
                PTOIdleRPMThresholdSubPage(),
                FirmBrakeDecelerationLimitSubPage()]

class Incident(DataPage):
    subpages = [SubPage(param_list=[EngineHours()]),
                SubPage(param_list=[Odometer()]),
                LastStopPage(),
                SubPage(param_list=[SampleCount()]),
                SubPage(param_list=[Timestamp()]),
                HardBrakePage(),
                SubPage(param_list=[Timestamp()])]

class TripTable(DataPage):
    subpages = [BrakeCountsSubPage(),
                HardBrakeCountsSubPage(),
                TimeInRoadSpeedEngineRPMBandsSubPage(),
                TimeInEngineLoadEngineRPMBandsSubPage(),
                TimeInAutomaticOverSpeedBandsSubPage(),
                TimeInAutomaticEngineOverRevBandsSubPage()]
                

class Trip(DataPage):
    subpages = [TripSubPage(),
                DriveSubPage(),
                CruiseSubPage(),
                TopGearSubPage(),
                IdleSubPage(),
                VSGPTOSubPage(),
                OverSpeedATimeSubPage(),
                OverSpeedBTimeSubPage(),
                OverRevTimeSubPage(),
                CoastTimeSubPage(),
                PeakSubPage(),
                InterruptSubPage(),
                TimeoutSubPage(),
                DriveLoadAccumulationSubPage(),
                HardBrakeCountSubPage(),
                OptimisedIdleData1SubPage(),
                TopGearRatioSubPage(),
                TopGearTimeStampSubPage(),
                TopGear1DistanceSubPage(),
                TopGear1RatioSubPage(),
                TopGearCruiseSubPage(),
                RSGSubPage(),
                StopIdleSubPage(),
                PumpSubPage(),
                JakeBrakeTimeSubPage(),
                FanTimeSubPage(),
                OptimisedIdleData2SubPage(),
                PeakTimeStampSubPage(),
                TripStartSubPage(),
                CountsSubPage(),
                BVESubPage(),
                AlertCountSubPage(),
                DriveAverageLoadFactorSubPage(),
                OptimizedIdleCountsSubPage(),
                DPFRegenerationStatisticsSubPage(),
                PredictiveCruiseSubPage()]

class Permanent(DataPage):
    subpages = [PermanentDataSubPage(),
                PermanentTotalIdleSubPage(),
                PermanentTotalVSGSubPage(),
                PermanentTotalCruiseTimeSubPage(),
                PermanentOptimizedIdleSubPage(),
                PermanentEngineBrakeTimeSubPage(),
                PermanentDriveAverageLoadFactorSubPage(),
                PermanentEngineRevolutionsSubPage(),
                PermanentFanTimeSubPage(),
                PermanentPeakSubPage(),
                PermanentOptimizedIdleCountsSubPage(),
                PermanentDPFRegenStatisticsSubPage(),
                PermanentTotalPredictiveCruiseTimeSubPage()]



request_codes = {1:Trip,#done
                 2:Incident,#done
                 3:Incident,#done
                 4:Incident,#done
                 6:ConfigurationData,#done
                 10:Header,
                 12:TripTable,#done
                 14:Trip,#done
                 15:DetailedAlert,#done
                 16:EngineUsage,
                 20:Permanent,#done
                 21:Trip,#done
                 22:TripTable,#done
                 23:Trip,#done
                 24:TripTable,#done
                 25:TripTable}#done



