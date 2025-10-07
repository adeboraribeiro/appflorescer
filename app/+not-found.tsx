import { Link, Stack } from 'expo-router';
import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

export default function NotFoundScreen() {
  return (
    <>
      <Stack.Screen options={{ title: 'Oops!' }} />
      <View style={styles.container}>
        <Text style={[styles.text, styles.title]}>This screen does not exist.</Text>
  <Link href="/" style={styles.link}>
          <Text style={styles.linkText}>Go to home screen</Text>
        </Link>
      </View>
    </>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 20,
  },
  text: {
    textAlign: 'center',
    marginBottom: 20,
  },
  link: {
    marginTop: 15,
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 6,
  },
  linkText: {
    color: '#0a7ea4',
    fontSize: 16,
    lineHeight: 30,
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    lineHeight: 32,
    textAlign: 'center',
    marginBottom: 20,
  },
});
