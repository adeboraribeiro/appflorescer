import { useRouter } from 'expo-router';
import { useEffect, useRef } from 'react';
import { Animated, Dimensions, StyleSheet } from 'react-native';
import Svg, { Circle, G, Path, Rect, Text } from 'react-native-svg';
import { useAuth } from '../../contexts/AuthContext';
import { useUser } from '../../contexts/UserContext';
import { ensureSupabaseConnected } from '../../lib/supabase';

// Create an animated version of G for the petals
const AnimatedG = Animated.createAnimatedComponent(G);

export default function SplashScreenComponent() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const { fetchUserProfile, loading: userLoading, needsOnboarding } = useUser();
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const footerFadeAnim = useRef(new Animated.Value(0)).current;
  const spinValue = useRef(new Animated.Value(0)).current;
  const slideFlowerAnim = useRef(new Animated.Value(-20)).current;
  const slideTextAnim = useRef(new Animated.Value(20)).current;

  // Calculate responsive dimensions
  const { width: screenWidth } = Dimensions.get('window');
  const svgWidth = screenWidth * 0.9;
  const svgAspectRatio = 500 / 150;
  const svgHeight = svgWidth / svgAspectRatio;

  // Handle user data fetching and app preparation
  useEffect(() => {
    let mounted = true;
    
    async function prepare() {
      try {
        // Start fetching user profile immediately if we have a user
        const profilePromise = user ? fetchUserProfile() : Promise.resolve();
        
        // Attempt to ensure the Supabase connection when splash is shown.
        // Run reconnect in parallel but don't block animations for too long.
        const reconnectPromise = ensureSupabaseConnected();
        
        // Allow reconnect attempt to run a short while in parallel with the splash animation
        await Promise.race([reconnectPromise, new Promise(resolve => setTimeout(resolve, 500))]);

        // Start fetching profile if authenticated, but do NOT wait for it beyond
        // the animation duration. All fetching should occur during the animation.
        const animationDurationMs = 4800;
        // profilePromise already started above; don't await it here so navigation
        // happens right after the fade.
        void profilePromise;

        // Wait only for the animation duration
        await new Promise(resolve => setTimeout(resolve, animationDurationMs));

        // Fade out animation (300ms) and wait for it to complete
        Animated.parallel([
          Animated.timing(fadeAnim, {
            toValue: 0,
            duration: 300,
            useNativeDriver: true,
          }),
          Animated.timing(footerFadeAnim, {
            toValue: 0,
            duration: 300,
            useNativeDriver: true,
          })
        ]).start();

        await new Promise(resolve => setTimeout(resolve, 300));
        
        // Only navigate if component is still mounted
        if (mounted) {
          router.replace(user ? '/(tabs)/home' : '/onboarding');
        }
      } catch (error) {
        console.error('Error preparing app:', error);
        if (mounted) {
          router.replace(user ? '/(tabs)/home' : '/onboarding');
        }
      }
    }
    
    prepare();
    
    return () => {
      mounted = false;
    };
  }, [user]);

  // Fade in and slide animations
  useEffect(() => {
    // Initial animations for logo
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 750,
        useNativeDriver: true,
      }),
      Animated.timing(slideFlowerAnim, {
        toValue: 0,
        duration: 750,
        useNativeDriver: true,
      }),
      Animated.timing(slideTextAnim, {
        toValue: 0,
        duration: 750,
        useNativeDriver: true,
      })
    ]).start();

    // Delayed footer animation
    setTimeout(() => {
      Animated.timing(footerFadeAnim, {
        toValue: 1,
        duration: 800,
        useNativeDriver: true,
      }).start();
    }, 1101);
  }, []);

  // Single spin animation for petals
  useEffect(() => {
    // Reset spin value at start
    spinValue.setValue(0);
    
    const spinAnimation = Animated.timing(spinValue, {
      toValue: 1,
      duration: 4500,
      useNativeDriver: true,
    });
    
    spinAnimation.start();
    
    return () => spinAnimation.stop();
  }, []);

  const spin = spinValue.interpolate({
    inputRange: [0, 1],
    outputRange: ['0deg', '360deg']
  });

  return (
    <Animated.View style={styles.container}>
      {/* Footer SVG */}
      <Animated.View style={[styles.footer, { opacity: footerFadeAnim }]}>
        <Svg width={280} height={40} viewBox="0 0 300 40">
          <Text 
            x="138" 
            y="28"
            textAnchor="middle"
            fontFamily="system-ui, -apple-system, sans-serif" 
            fontSize="16" 
            fontWeight="100" 
            fill="#047857"
            letterSpacing="0.5"
          >
            FEITO COM AMOR NO
          </Text>
          
          {/* Brazilian Flag */}
          <G transform="translate(225, 12)">
            <Rect x="0" y="0" width="24" height="20" rx="2" fill="#009B3A"/>
            <Path d="M12 3 L21 10 L12 17 L3 10 Z" fill="#FFDF00"/>
            <Circle cx="12" cy="10" r="4.2" fill="#002776"/>
            <Path d="M6 9 L18 9" stroke="#FFFFFF" strokeWidth="0.6"/>
          </G>
        </Svg>
      </Animated.View>
      
      <Animated.View style={{ opacity: fadeAnim }}>
        <Svg
          width={svgWidth}
          height={svgHeight}
          viewBox="0 0 500 150"
          preserveAspectRatio="xMidYMid meet"
        >
          {/* Flower icon group */}
          <AnimatedG transform={[
            { translateX: Animated.add(129, slideFlowerAnim) },
            { translateY: 75 }
          ]}>
            {/* ONLY the petals rotate */}
            <AnimatedG transform={[{ rotate: spin }]}>
              <Circle cx="0" cy="-20" r="8" fill="#10B981" />
              <Circle cx="17" cy="-10" r="8" fill="#34D399" />
              <Circle cx="17" cy="10" r="8" fill="#6EE7B7" />
              <Circle cx="0" cy="20" r="8" fill="#059669" />
              <Circle cx="-17" cy="10" r="8" fill="#047857" />
              <Circle cx="-17" cy="-10" r="8" fill="#22C55E" />
            </AnimatedG>
            {/* Center remains stationary */}
            <Circle cx="0" cy="0" r="6" fill="#1F2937" />
          </AnimatedG>
          
          {/* Logo typography */}
          <AnimatedG transform={[{ translateX: slideTextAnim }]}>
            <Text
              x="179"
              y="93"
              fontFamily="system-ui, -apple-system, sans-serif"
              fontSize="52"
              fontWeight="900"
              fill="#059669"
            >
              Florescer
            </Text>
          </AnimatedG>
        </Svg>
      </Animated.View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: { 
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#ffffff',
    elevation: 999,
    zIndex: 999,
  },
  footer: {
    position: 'absolute',
    bottom: 40,
    left: 0,
    right: 0,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 20
  }
});
