/** Set before post-login navigation so home page does not override the target route. */
export const SKIP_HOME_REDIRECT_KEY = "fp_skip_home_redirect";

export function consumeSkipHomeRedirect(): boolean {
  if (typeof sessionStorage === "undefined") return false;
  if (!sessionStorage.getItem(SKIP_HOME_REDIRECT_KEY)) return false;
  sessionStorage.removeItem(SKIP_HOME_REDIRECT_KEY);
  return true;
}
