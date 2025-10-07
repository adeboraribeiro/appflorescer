import { Stack } from 'expo-router';
import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import '../app/i18n';
import SettingsModal from '../components/SettingsModal';
import { AuthProvider } from '../contexts/AuthContext';
import { SettingsProvider } from '../contexts/SettingsContext';
import { ThemeProvider, useTheme } from '../contexts/ThemeContext';
import { UserProvider } from '../contexts/UserContext';
import { NotificationProvider } from './contexts/NotificationContext';

function NavigationContent() {
  const { theme } = useTheme();
  const bg = theme === 'dark' ? '#0A1E1C' : '#F7FFFC';
  
  return (
    <Stack
      screenOptions={{
        headerShown: false,
        contentStyle: {
          backgroundColor: bg,
        },
        animation: 'fade',
        animationDuration: 200
      }}
  // initialRouteName removed — project no longer uses a separate splash route
    >
      <Stack.Screen 
        name="(tabs)" 
        options={{
          animation: 'fade',
          animationDuration: 300,
          gestureEnabled: false,
          headerBackVisible: false
        }} 
      />
      <Stack.Screen name="screens/LoginScreen" 
        options={{
          animation: 'fade',
          animationDuration: 200,
          presentation: 'transparentModal'
        }}
      />
      <Stack.Screen 
        name="account" 
        options={{
          animation: 'fade',
          animationDuration: 200,
          presentation: 'transparentModal'
        }}
      />
    </Stack>
  );
}

// Minimal class-based error boundary so we can surface runtime errors in-app
class ErrorCatcher extends React.Component<{ label?: string; children?: React.ReactNode }, { error: Error | null }> {
  constructor(props: any) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(err: Error) {
    return { error: err };
  }

  componentDidCatch(err: Error, info: any) {
    // Log and swallow so UI can show a helpful message
    // eslint-disable-next-line no-console
    console.error('[ErrorCatcher]', this.props.label ?? 'unknown', err, info);
  }

  render() {
    if (this.state.error) {
      return (
        <View style={styles.errContainer}>
          <Text style={styles.errTitle}>Runtime error</Text>
          <Text style={styles.errLabel}>{this.props.label}</Text>
          <Text style={styles.errMsg}>{String(this.state.error?.message ?? this.state.error)}</Text>
        </View>
      );
    }
    // @ts-ignore children are valid
    return this.props.children ?? null;
  }
}

const styles = StyleSheet.create({
  errContainer: { flex: 1, padding: 20, backgroundColor: '#fff', justifyContent: 'center' },
  errTitle: { fontSize: 20, fontWeight: '700', marginBottom: 8, color: '#b91c1c' },
  errLabel: { fontSize: 14, marginBottom: 8, color: '#374151' },
  errMsg: { fontSize: 13, color: '#111827' },
});

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <ErrorCatcher label="ThemeProvider">
        <ThemeProvider>
          <ErrorCatcher label="ThemedApp">
            {/* ThemedApp ensures the root background follows the current theme immediately */}
            <ThemedApp>
              <ErrorCatcher label="AuthProvider">
                <AuthProvider>
                  <ErrorCatcher label="UserProvider">
                    <UserProvider>
                      <ErrorCatcher label="SettingsProvider">
                        <SettingsProvider>
                          <NavigationContent />
                          <SettingsModal />
                        </SettingsProvider>
                      </ErrorCatcher>
                    </UserProvider>
                  </ErrorCatcher>
                </AuthProvider>
              </ErrorCatcher>
            </ThemedApp>
          </ErrorCatcher>
        </ThemeProvider>
      </ErrorCatcher>
    </SafeAreaProvider>
  );
}

function ThemedApp({ children }: { children: React.ReactNode }) {
  const { theme } = useTheme();
  const bg = theme === 'dark' ? '#0A1E1C' : '#F7FFFC';
  return (
    <View style={{ flex: 1, backgroundColor: bg }}>
      <NotificationProvider theme={theme}>{children}</NotificationProvider>
    </View>
  );
}