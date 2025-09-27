export type AppRole = 'member' | 'merchant' | 'enterprise_admin';
export const ROLE = { MEMBER:'member', MERCHANT:'merchant', ENTERPRISE_ADMIN:'enterprise_admin' } as const;
export function hasAnyRole(userRoles: string[], allow: AppRole[]) { return allow.some(r => userRoles.includes(r)); }
