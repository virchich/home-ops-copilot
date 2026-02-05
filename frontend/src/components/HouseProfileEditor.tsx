import { useState } from 'react';
import type { HouseProfile, ClimateZone, HouseType, InstalledSystem } from '../types';

interface HouseProfileEditorProps {
  profile: HouseProfile;
  onSave: (profile: HouseProfile) => void;
  onCancel: () => void;
  isSaving?: boolean;
}

const climateZones: { value: ClimateZone; label: string }[] = [
  { value: 'cold', label: 'Cold (Northern US, Canada)' },
  { value: 'mixed', label: 'Mixed (Mid-Atlantic, Midwest)' },
  { value: 'hot_humid', label: 'Hot Humid (Florida, Gulf Coast)' },
  { value: 'hot_dry', label: 'Hot Dry (Arizona, Nevada)' },
];

const houseTypes: { value: HouseType; label: string }[] = [
  { value: 'single_family', label: 'Single Family' },
  { value: 'townhouse', label: 'Townhouse' },
  { value: 'condo', label: 'Condo' },
  { value: 'duplex', label: 'Duplex' },
];

const deviceTypes = [
  'furnace',
  'thermostat',
  'hrv',
  'humidifier',
  'water_heater',
  'water_softener',
  'energy_meter',
  'air_conditioner',
  'heat_pump',
  'boiler',
];

interface SystemRow {
  device_type: string;
  system: InstalledSystem | null;
}

export function HouseProfileEditor({ profile, onSave, onCancel, isSaving }: HouseProfileEditorProps) {
  const [editedProfile, setEditedProfile] = useState<HouseProfile>({ ...profile });
  const [systems, setSystems] = useState<SystemRow[]>(() => {
    return Object.entries(profile.systems).map(([device_type, system]) => ({
      device_type,
      system,
    }));
  });

  const handleAddSystem = () => {
    const availableTypes = deviceTypes.filter(
      (dt) => !systems.some((s) => s.device_type === dt)
    );
    if (availableTypes.length > 0) {
      setSystems([...systems, { device_type: availableTypes[0], system: null }]);
    }
  };

  const handleRemoveSystem = (index: number) => {
    setSystems(systems.filter((_, i) => i !== index));
  };

  const handleSystemChange = (index: number, field: keyof SystemRow, value: string) => {
    const newSystems = [...systems];
    if (field === 'device_type') {
      newSystems[index] = { ...newSystems[index], device_type: value };
    }
    setSystems(newSystems);
  };

  const handleSystemDetailChange = (
    index: number,
    field: keyof InstalledSystem,
    value: string | number | null
  ) => {
    const newSystems = [...systems];
    const currentSystem = newSystems[index].system || {
      model: null,
      manufacturer: null,
      fuel_type: null,
      install_year: null,
      notes: null,
    };
    newSystems[index] = {
      ...newSystems[index],
      system: { ...currentSystem, [field]: value || null },
    };
    setSystems(newSystems);
  };

  const handleSave = () => {
    const systemsMap: Record<string, InstalledSystem | null> = {};
    systems.forEach((s) => {
      systemsMap[s.device_type] = s.system;
    });

    onSave({
      ...editedProfile,
      systems: systemsMap,
    });
  };

  return (
    <div className="space-y-6">
      {/* Basic Info */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            House Name
          </label>
          <input
            type="text"
            value={editedProfile.name}
            onChange={(e) => setEditedProfile({ ...editedProfile, name: e.target.value })}
            className="w-full px-3 py-2 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Year Built
          </label>
          <input
            type="number"
            value={editedProfile.year_built || ''}
            onChange={(e) =>
              setEditedProfile({
                ...editedProfile,
                year_built: e.target.value ? parseInt(e.target.value) : null,
              })
            }
            className="w-full px-3 py-2 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Climate Zone
          </label>
          <select
            value={editedProfile.climate_zone}
            onChange={(e) =>
              setEditedProfile({ ...editedProfile, climate_zone: e.target.value as ClimateZone })
            }
            className="w-full px-3 py-2 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            {climateZones.map((cz) => (
              <option key={cz.value} value={cz.value}>
                {cz.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            House Type
          </label>
          <select
            value={editedProfile.house_type}
            onChange={(e) =>
              setEditedProfile({ ...editedProfile, house_type: e.target.value as HouseType })
            }
            className="w-full px-3 py-2 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            {houseTypes.map((ht) => (
              <option key={ht.value} value={ht.value}>
                {ht.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Systems */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            Installed Systems
          </label>
          <button
            onClick={handleAddSystem}
            className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300"
          >
            + Add System
          </button>
        </div>

        <div className="space-y-3">
          {systems.map((row, index) => (
            <div
              key={index}
              className="p-3 rounded-md border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50"
            >
              <div className="flex items-center justify-between mb-2">
                <select
                  value={row.device_type}
                  onChange={(e) => handleSystemChange(index, 'device_type', e.target.value)}
                  className="px-2 py-1 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
                >
                  {deviceTypes.map((dt) => (
                    <option key={dt} value={dt}>
                      {dt.replace('_', ' ')}
                    </option>
                  ))}
                </select>
                <button
                  onClick={() => handleRemoveSystem(index)}
                  className="text-red-500 hover:text-red-700 text-sm"
                >
                  Remove
                </button>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                <input
                  type="text"
                  placeholder="Manufacturer"
                  value={row.system?.manufacturer || ''}
                  onChange={(e) => handleSystemDetailChange(index, 'manufacturer', e.target.value)}
                  className="px-2 py-1 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
                />
                <input
                  type="text"
                  placeholder="Model"
                  value={row.system?.model || ''}
                  onChange={(e) => handleSystemDetailChange(index, 'model', e.target.value)}
                  className="px-2 py-1 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
                />
                <input
                  type="text"
                  placeholder="Fuel type"
                  value={row.system?.fuel_type || ''}
                  onChange={(e) => handleSystemDetailChange(index, 'fuel_type', e.target.value)}
                  className="px-2 py-1 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
                />
                <input
                  type="number"
                  placeholder="Install year"
                  value={row.system?.install_year || ''}
                  onChange={(e) =>
                    handleSystemDetailChange(
                      index,
                      'install_year',
                      e.target.value ? parseInt(e.target.value) : null
                    )
                  }
                  className="px-2 py-1 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
                />
              </div>
            </div>
          ))}

          {systems.length === 0 && (
            <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
              No systems added. Click "Add System" to add your home's equipment.
            </p>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
        <button
          onClick={onCancel}
          disabled={isSaving}
          className="px-4 py-2 text-sm font-medium rounded-md bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="px-4 py-2 text-sm font-medium rounded-md bg-blue-600 text-white hover:bg-blue-700 transition-colors disabled:opacity-50"
        >
          {isSaving ? 'Saving...' : 'Save Changes'}
        </button>
      </div>
    </div>
  );
}
