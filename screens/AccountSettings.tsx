import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

export const AccountSettings = () => {
  return (
    <View style={styles.container}>
      <Text style={styles.text}>Account Settings</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0A1E1C',
    padding: 20,
  },
  text: {
    color: '#E0F7F4',
    fontSize: 20,
  },
});