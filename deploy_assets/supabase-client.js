// ═══════════════════════════════════════════════════════════════════════
//  ☁️ FTMO TRACKER PRO — SUPABASE CLIENT
//  Standalone JS module for static HTML pages.
//  Handles auth, cloud sync, and subscription management.
// ═══════════════════════════════════════════════════════════════════════

// ── Configuration ────────────────────────────────────────────────────
// These are set at deploy time via Netlify env vars or injected during build.
// For local dev, set them in a script tag before including this file.
const SUPABASE_CONFIG = {
  url: window.__SUPABASE_URL__ || '',
  anonKey: window.__SUPABASE_ANON_KEY__ || '',
};

const STORAGE_KEY = 'ftmoTracker';       // Local state key
const AUTH_KEY = 'ftmoAuth';             // Cached auth session

// ── Supabase Client (loaded dynamically if CDN not available) ────────
let _supabase = null;

function getClient() {
  if (_supabase) return _supabase;
  if (typeof supabase !== 'undefined' && SUPABASE_CONFIG.url && SUPABASE_CONFIG.anonKey) {
    _supabase = supabase.createClient(SUPABASE_CONFIG.url, SUPABASE_CONFIG.anonKey, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
      },
    });
  }
  return _supabase;
}

// ── Auth ─────────────────────────────────────────────────────────────
const supabaseClient = {
  /** Check if Supabase is configured */
  isConfigured() {
    return !!(SUPABASE_CONFIG.url && SUPABASE_CONFIG.anonKey);
  },

  /** Get current auth session */
  async getSession() {
    const client = getClient();
    if (!client) return null;
    try {
      const { data } = await client.auth.getSession();
      return data.session;
    } catch {
      return null;
    }
  },

  /** Get current user */
  async getUser() {
    const session = await this.getSession();
    return session?.user || null;
  },

  /** Sign up with email + password */
  async signUp(email, password) {
    const client = getClient();
    if (!client) throw new Error('Supabase not configured');
    const { data, error } = await client.auth.signUp({
      email,
      password,
      options: { emailRedirectTo: window.location.origin + '/ftmo_challenge_tracker.html' },
    });
    if (error) throw error;
    return data;
  },

  /** Sign in with email + password */
  async signIn(email, password) {
    const client = getClient();
    if (!client) throw new Error('Supabase not configured');
    const { data, error } = await client.auth.signInWithPassword({ email, password });
    if (error) throw error;
    return data;
  },

  /** Sign in with magic link */
  async signInWithMagicLink(email) {
    const client = getClient();
    if (!client) throw new Error('Supabase not configured');
    const { error } = await client.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: window.location.origin + '/ftmo_challenge_tracker.html' },
    });
    if (error) throw error;
    return true;
  },

  /** Sign out */
  async signOut() {
    const client = getClient();
    if (!client) return;
    await client.auth.signOut();
    localStorage.removeItem(AUTH_KEY);
  },

  /** Listen to auth state changes */
  onAuthStateChange(callback) {
    const client = getClient();
    if (!client) return () => {};
    const { data } = client.auth.onAuthStateChange((event, session) => {
      callback(event, session);
    });
    return data.subscription.unsubscribe;
  },

  // ── Challenges CRUD ──────────────────────────────────────────────

  /** Get all challenges for current user */
  async getChallenges() {
    const client = getClient();
    const user = await this.getUser();
    if (!client || !user) return [];
    const { data } = await client
      .from('challenges')
      .select('*')
      .eq('user_id', user.id)
      .order('created_at', { ascending: false });
    return data || [];
  },

  /** Create or update a challenge */
  async saveChallenge(challenge) {
    const client = getClient();
    const user = await this.getUser();
    if (!client || !user) throw new Error('Not authenticated');

    const record = {
      user_id: user.id,
      challenge_type: challenge.challengeType,
      account_size: challenge.accountSize,
      start_balance: challenge.startBalance,
      phase: challenge.phase || 1,
      status: challenge.status || 'active',
    };

    if (challenge.id) {
      // Update existing
      const { data, error } = await client
        .from('challenges')
        .update(record)
        .eq('id', challenge.id)
        .eq('user_id', user.id)
        .select()
        .single();
      if (error) throw error;
      return data;
    } else {
      // Create new
      const { data, error } = await client
        .from('challenges')
        .insert(record)
        .select()
        .single();
      if (error) throw error;
      return data;
    }
  },

  /** Delete a challenge */
  async deleteChallenge(challengeId) {
    const client = getClient();
    const user = await this.getUser();
    if (!client || !user) throw new Error('Not authenticated');
    const { error } = await client
      .from('challenges')
      .delete()
      .eq('id', challengeId)
      .eq('user_id', user.id);
    if (error) throw error;
  },

  // ── Trades CRUD ──────────────────────────────────────────────────

  /** Get trades for a challenge */
  async getTrades(challengeId) {
    const client = getClient();
    const user = await this.getUser();
    if (!client || !user) return [];
    const { data } = await client
      .from('trades')
      .select('*')
      .eq('challenge_id', challengeId)
      .eq('user_id', user.id)
      .order('trade_date', { ascending: true });
    return data || [];
  },

  /** Save a trade */
  async saveTrade(trade) {
    const client = getClient();
    const user = await this.getUser();
    if (!client || !user) throw new Error('Not authenticated');

    const record = {
      challenge_id: trade.challengeId,
      user_id: user.id,
      trade_date: trade.date,
      balance: trade.balance,
      notes: trade.notes || '',
    };

    if (trade.id) {
      const { data, error } = await client
        .from('trades')
        .update(record)
        .eq('id', trade.id)
        .eq('user_id', user.id)
        .select()
        .single();
      if (error) throw error;
      return data;
    } else {
      const { data, error } = await client
        .from('trades')
        .insert(record)
        .select()
        .single();
      if (error) throw error;
      return data;
    }
  },

  /** Delete a trade */
  async deleteTrade(tradeId) {
    const client = getClient();
    const user = await this.getUser();
    if (!client || !user) throw new Error('Not authenticated');
    const { error } = await client
      .from('trades')
      .delete()
      .eq('id', tradeId)
      .eq('user_id', user.id);
    if (error) throw error;
  },

  // ── Cloud Sync ───────────────────────────────────────────────────

  /** Full sync: push local data to cloud, pull cloud data to local */
  async syncWithCloud() {
    const user = await this.getUser();
    if (!user) return { success: false, reason: 'not_authenticated' };

    // Push local state to cloud
    const localState = this._loadLocalState();
    if (localState && localState.trades && localState.trades.length > 0) {
      // Find or create a challenge
      let challenges = await this.getChallenges();
      let challenge = challenges.find(c =>
        c.challenge_type === localState.challengeType &&
        c.account_size === localState.accountSize &&
        c.start_balance === localState.startBalance
      );

      if (!challenge) {
        challenge = await this.saveChallenge({
          challengeType: localState.challengeType,
          accountSize: localState.accountSize,
          startBalance: localState.startBalance,
          phase: localState.phase || 1,
        });
      }

      // Push trades
      const cloudTrades = await this.getTrades(challenge.id);
      const cloudTradeDates = new Set(cloudTrades.map(t => t.trade_date));

      for (const trade of localState.trades) {
        if (!cloudTradeDates.has(trade.date)) {
          await this.saveTrade({
            challengeId: challenge.id,
            date: trade.date,
            balance: trade.balance,
            notes: trade.notes || '',
          });
        }
      }

      // Update status
      if (localState.challengeType === '2step') {
        await this.saveChallenge({
          id: challenge.id,
          challengeType: challenge.challenge_type,
          accountSize: challenge.account_size,
          startBalance: challenge.start_balance,
          phase: localState.phase || challenge.phase,
        });
      }

      return { success: true, challengeId: challenge.id };
    }

    // Pull cloud data to local
    const challenges = await this.getChallenges();
    if (challenges.length > 0) {
      const latest = challenges[0];
      const trades = await this.getTrades(latest.id);
      if (trades.length > 0) {
        const localState = {
          challengeType: latest.challenge_type,
          accountSize: latest.account_size,
          startBalance: parseFloat(latest.start_balance),
          phase: latest.phase,
          currentBalance: parseFloat(trades[trades.length - 1].balance),
          trades: trades.map(t => ({
            date: t.trade_date,
            balance: parseFloat(t.balance),
            notes: t.notes || '',
          })),
          cloudId: latest.id,
        };
        this._saveLocalState(localState);
        return { success: true, syncedFromCloud: true };
      }
    }

    return { success: true, nothingToSync: true };
  },

  /** Check if the current user has an active Pro subscription */
  async checkProStatus() {
    const client = getClient();
    const user = await this.getUser();
    if (!client || !user) return false;
    const { data } = await client
      .from('subscriptions')
      .select('status')
      .eq('user_id', user.id)
      .eq('status', 'active')
      .maybeSingle();
    return !!data;
  },

  /** Join the waitlist */
  async joinWaitlist(email, name = '') {
    const client = getClient();
    if (!client) throw new Error('Supabase not configured');
    const { error } = await client
      .from('waitlist')
      .insert({ email, name })
      .select()
      .single();
    if (error && error.code !== '23505') throw error; // Ignore duplicate emails
    return true;
  },

  // ── Internal helpers ─────────────────────────────────────────────

  _loadLocalState() {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  },

  _saveLocalState(state) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {}
  },
};

// ── Ready flag: set to true after CDN loads (prevents race conditions) ───
window.__supabaseReady = false;

// ── Auto-load Supabase CDN if configured ────────────────────────────
(function autoLoad() {
  if (!SUPABASE_CONFIG.url || !SUPABASE_CONFIG.anonKey) {
    // Not configured — mark ready and let trackers hide auth features
    window.__supabaseReady = true;
    return;
  }
  if (typeof supabase === 'undefined') {
      const script = document.createElement('script');
      script.src = 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/dist/umd/supabase.js';
      script.onload = () => {
        _supabase = null;
        getClient();
        window.__supabaseReady = true;
        window.dispatchEvent(new CustomEvent('supabase-loaded'));
      };
      script.onerror = () => {
        console.warn('[Supabase] CDN failed to load. Auth/cloud features disabled.');
        window.supabaseClient = { isConfigured: () => false };
        window.__supabaseReady = true;
        window.dispatchEvent(new CustomEvent('supabase-loaded'));
      };
      document.head.appendChild(script);
    } else {
      _supabase = null;
      getClient();
      window.__supabaseReady = true;
      window.dispatchEvent(new CustomEvent('supabase-loaded'));
    }
  }
})();

// Export to global scope
window.supabaseClient = supabaseClient;
