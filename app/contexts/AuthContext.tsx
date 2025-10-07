// Re-export the canonical context implementation located at the repository root.
// This file intentionally forwards all named exports so existing relative
// imports inside `app/...` (for example `../contexts/AuthContext`) keep
// working regardless of whether the canonical implementation lives in
// `/contexts/AuthContext.tsx`.

export * from '../../contexts/AuthContext';
