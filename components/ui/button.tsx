import { Pressable, PressableProps, StyleSheet, ViewStyle } from 'react-native';

interface ButtonProps extends PressableProps {
  variant?: 'default' | 'outline' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  style?: ViewStyle;
}

export const Button = ({ 
  children, 
  variant = 'default',
  size = 'md',
  style,
  ...props 
}: ButtonProps) => {
  return (
    <Pressable
      style={({ pressed }) => [
        styles.button,
        styles[variant],
        styles[size],
        style,
        pressed && styles.pressed
      ]}
      {...props}
    >
      {children}
    </Pressable>
  );
};

const styles = StyleSheet.create({
  button: {
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  default: {
    backgroundColor: '#007AFF',
  },
  outline: {
    borderWidth: 1,
    borderColor: '#007AFF',
  },
  ghost: {
    backgroundColor: 'transparent',
  },
  pressed: {
    opacity: 0.7,
  },
  sm: {
    paddingVertical: 6,
    paddingHorizontal: 12,
  },
  md: {
    paddingVertical: 8,
    paddingHorizontal: 16,
  },
  lg: {
    paddingVertical: 10,
    paddingHorizontal: 20,
  },
});