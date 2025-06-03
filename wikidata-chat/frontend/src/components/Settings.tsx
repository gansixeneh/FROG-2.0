// frontend/src/components/Settings.tsx
import React from 'react';
import { useChat } from '../context/ChatContext';

interface SettingsProps {
  isOpen: boolean;
  onClose: () => void;
}

const Settings: React.FC<SettingsProps> = ({ isOpen, onClose }) => {
  const { settings, updateSettings } = useChat();

  if (!isOpen) return null;

  const handleToggle = (setting: 'useVerbalization' | 'useGoogleSearch') => {
    updateSettings({
      ...settings,
      [setting]: !settings[setting]
    });
  };

  const handleSourceChange = (source: 'wikidata' | 'curriculum') => {
    updateSettings({
      ...settings,
      knowledgeSource: source
    });
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-frog-dark flex items-center">
            <svg 
              width="24" 
              height="24" 
              viewBox="0 0 24 24" 
              fill="none" 
              stroke="currentColor" 
              strokeWidth="2" 
              className="mr-2"
            >
              <circle cx="12" cy="12" r="3"/>
              <path d="M12 1v6m0 6v6m11-7h-6m-6 0H1"/>
            </svg>
            FrOG Settings
          </h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full"
          >
            <svg 
              width="20" 
              height="20" 
              viewBox="0 0 24 24" 
              fill="none" 
              stroke="currentColor" 
              strokeWidth="2"
            >
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Column: Knowledge Source */}
          <div className="p-4 bg-gray-50 rounded-lg">
            <h3 className="text-lg font-medium text-gray-900 mb-3">Knowledge Source</h3>
            <p className="text-sm text-gray-500 mb-4">
              Select the knowledge source to use for answering questions. Each source has different data and capabilities.
            </p>
            <div className="space-y-3">
              <label className="flex items-start p-3 border rounded-lg cursor-pointer hover:bg-gray-50 transition-colors">
                <input 
                  type="radio" 
                  checked={settings.knowledgeSource === 'wikidata'} 
                  onChange={() => handleSourceChange('wikidata')}
                  className="form-radio h-5 w-5 text-frog-dark mt-0.5 flex-shrink-0"
                />
                <div className="ml-3">
                  <div className="font-medium text-gray-900">Wikidata</div>
                  <div className="text-sm text-gray-500">Comprehensive public knowledge graph with references</div>
                </div>
              </label>
              <label className="flex items-start p-3 border rounded-lg cursor-pointer hover:bg-gray-50 transition-colors">
                <input 
                  type="radio" 
                  checked={settings.knowledgeSource === 'curriculum'} 
                  onChange={() => handleSourceChange('curriculum')}
                  className="form-radio h-5 w-5 text-frog-dark mt-0.5 flex-shrink-0" 
                />
                <div className="ml-3">
                  <div className="font-medium text-gray-900">Curriculum</div>
                  <div className="text-sm text-gray-500">University curriculum knowledge graph (https://generous-lark-duly.ngrok-free.app/curi/query)</div>
                </div>
              </label>
            </div>
          </div>

          {/* Right Column: Settings Toggles */}
          <div className="space-y-4">
            {/* Use Verbalization Setting */}
            <div className="p-4 bg-gray-50 rounded-lg">
              <div className="flex items-start justify-between">
                <div className="flex-1 pr-4">
                  <h3 className="text-lg font-medium text-gray-900 mb-2">Use Verbalization</h3>
                  <p className="text-sm text-gray-500 mb-3">
                    When enabled, FrOG will try to answer simple questions using entity verbalization before generating SPARQL queries. 
                    When disabled, FrOG will always generate SPARQL queries directly.
                  </p>
                  <span className={`inline-block px-3 py-1 rounded-full text-xs font-medium ${
                    settings.useVerbalization ? 'bg-green-100 text-green-800' : 'bg-orange-100 text-orange-800'
                  }`}>
                    {settings.useVerbalization ? 'Enabled: Uses both verbalization and SPARQL' : 'Disabled: SPARQL queries only'}
                  </span>
                </div>
                <div className="flex-shrink-0">
                  <button
                    onClick={() => handleToggle('useVerbalization')}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-frog-DEFAULT focus:ring-offset-2 ${
                      settings.useVerbalization ? 'bg-frog-light' : 'bg-gray-300'
                    }`}
                    role="switch"
                    aria-checked={settings.useVerbalization}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full shadow-lg transition-transform ${
                        settings.useVerbalization 
                          ? 'translate-x-6 bg-frog-dark' 
                          : 'translate-x-1 bg-gray-600'
                      }`}
                    />
                  </button>
                </div>
              </div>
            </div>

            {/* Google Search Setting */}
            <div className="p-4 bg-gray-50 rounded-lg">
              <div className="flex items-start justify-between">
                <div className="flex-1 pr-4">
                  <h3 className="text-lg font-medium text-gray-900 mb-2">Google Search Fallback</h3>
                  <p className="text-sm text-gray-500 mb-3">
                    When enabled, FrOG will use Google Search as a fallback when knowledge graph methods fail to provide sufficient results. 
                    When disabled, FrOG will only use knowledge graph sources.
                  </p>
                  <span className={`inline-block px-3 py-1 rounded-full text-xs font-medium ${
                    settings.useGoogleSearch ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                  }`}>
                    {settings.useGoogleSearch ? 'Enabled: Uses Google Search as fallback' : 'Disabled: Knowledge Graph only'}
                  </span>
                </div>
                <div className="flex-shrink-0">
                  <button
                    onClick={() => handleToggle('useGoogleSearch')}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-frog-DEFAULT focus:ring-offset-2 ${
                      settings.useGoogleSearch ? 'bg-frog-light' : 'bg-gray-300'
                    }`}
                    role="switch"
                    aria-checked={settings.useGoogleSearch}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full shadow-lg transition-transform ${
                        settings.useGoogleSearch 
                          ? 'translate-x-6 bg-frog-dark' 
                          : 'translate-x-1 bg-gray-600'
                      }`}
                    />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-8 flex justify-end">
          <button
            onClick={onClose}
            className="px-6 py-2 bg-frog-DEFAULT text-white rounded-md hover:bg-frog-dark transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};

export default Settings;