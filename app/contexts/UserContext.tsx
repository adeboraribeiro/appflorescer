// Re-export the canonical UserContext implementation at the repository root so
// imports inside the `app/` folder like `../contexts/UserContext` continue to
// work without duplicating provider instances.

export * from '../../contexts/UserContext';
