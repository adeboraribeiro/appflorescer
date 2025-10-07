import React, { createContext, useContext, useState } from 'react';

type SettingsContextType = {
  isSettingsOpen: boolean;
  openSettings: () => void;
  closeSettings: () => void;
};

const SettingsContext = createContext<SettingsContextType>({
  isSettingsOpen: false,
  openSettings: () => {},
  closeSettings: () => {},
});

export const SettingsProvider = ({ children }: { children: React.ReactNode }) => {
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  const openSettings = () => {
    console.log('Opening settings...');
    setIsSettingsOpen(true);
  };

  const closeSettings = () => {
    console.log('Closing settings...');
    setIsSettingsOpen(false);
  };

  return (
    <SettingsContext.Provider value={{ isSettingsOpen, openSettings, closeSettings }}>
      {children}
    </SettingsContext.Provider>
  );
};

export const useSettings = () => useContext(SettingsContext);

// Default export to satisfy Expo Router when scanning files under app/
export default SettingsProvider;

// Example of how the settings button should be implemented
// import { useSettings } from '../../contexts/SettingsContext';

// // Inside your component:
// const { openSettings } = useSettings();

// <TouchableOpacity onPress={openSettings}>
//   <Ionicons name="settings-outline" size={24} color="#80E6D9" />
// </TouchableOpacity>