import * as Notifications from 'expo-notifications';
import { AppState } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { getRemindersForUser, ReminderEntry } from './api';

const TITLE = 'Time to take your medication!';
const STORAGE_KEY = (reminderId: number) => `notif:${reminderId}`;

// If server timestamp lacks timezone info, append EST offset (-05:00).
function ensureEstOffset(iso: string): string {
  if (!iso || typeof iso !== 'string') return iso;
  const s = iso.trim();
  // ends with Z or +HH:MM or -HH:MM
  if (/[Zz]$/.test(s) || /[+\-]\d{2}:\d{2}$/.test(s)) return s;
  return `${s}-05:00`;
}

// Compose notification body from reminder entry
function composeBody(r: ReminderEntry) {
  const main = [r.med_name, r.dosage].filter(Boolean).join(' ');
  return r.message ? `${main} — ${r.message}` : main;
}

function isValidReminder(r: any): r is ReminderEntry {
  return r && typeof r.trigger_time === 'string' && typeof r.med_name === 'string';
}

async function saveMapping(reminderId: number, localId: string) {
  try {
    await AsyncStorage.setItem(STORAGE_KEY(reminderId), localId);
  } catch (e) {
    // ignore storage errors
  }
}

async function getMapping(reminderId: number): Promise<string | null> {
  try {
    return await AsyncStorage.getItem(STORAGE_KEY(reminderId));
  } catch (e) {
    return null;
  }
}

async function removeMapping(reminderId: number) {
  try {
    await AsyncStorage.removeItem(STORAGE_KEY(reminderId));
  } catch (e) {
    // ignore
  }
}

/**
 * Schedule a single local notification from a server reminder entry.
 * If the server provided a reminder_id and we already have a mapping, do nothing.
 */
export async function scheduleLocalReminder(r: ReminderEntry) {
  if (!isValidReminder(r)) return null;
  const normalized = ensureEstOffset(r.trigger_time);
  const dt = new Date(normalized);
  if (isNaN(dt.getTime())) {
    console.warn('scheduleLocalReminder: invalid date for reminder', r, 'normalized:', normalized);
    return null;
  }

  // skip past triggers (30s tolerance)
  if (dt.getTime() < Date.now() - 30_000) {
    console.log('scheduleLocalReminder: skipping past reminder', r);
    return null;
  }

  // dedupe by stored mapping if server provided reminder_id
  if (typeof r.reminder_id === 'number') {
    const mapped = await getMapping(r.reminder_id);
    if (mapped) {
      console.log('scheduleLocalReminder: already scheduled (mapping)', r.reminder_id, mapped);
      return mapped; // already scheduled
    }
  }

  const body = composeBody(r);
  try {
    console.log('scheduleLocalReminder: scheduling', { reminder_id: r.reminder_id, trigger_time: r.trigger_time, normalized });
    const localId = await Notifications.scheduleNotificationAsync({
      content: {
        title: TITLE,
        body,
        sound: 'default',
        data: { reminder_id: r.reminder_id ?? null, trigger_time: r.trigger_time, med_name: r.med_name },
      },
      // prefer Date trigger directly (use normalized ISO with timezone)
      trigger: new Date(normalized) as any,
    });

    console.log('scheduleLocalReminder: scheduled localId', localId);
    if (typeof r.reminder_id === 'number') {
      await saveMapping(r.reminder_id, localId);
    }
    return localId;
  } catch (e) {
    console.error('scheduleLocalReminder: scheduleNotificationAsync failed', e);
    return null;
  }
}

export async function restoreScheduledReminders(userId: number) {
  try {
    const list = await getRemindersForUser(userId);
    console.log('restoreScheduledReminders: fetched', Array.isArray(list) ? list.length : typeof list, 'entries', list);
    if (!Array.isArray(list)) return;

    for (const r of list) {
      try {
        if (!isValidReminder(r)) {
          console.warn('restoreScheduledReminders: invalid reminder item, skipping', r);
          continue;
        }
        const dt = new Date(r.trigger_time);
        console.log('restoreScheduledReminders: processing reminder', { reminder_id: r.reminder_id, trigger_time: r.trigger_time, parsed: dt });
        const result = await scheduleLocalReminder(r);
        if (!result) console.warn('restoreScheduledReminders: scheduling returned null for', r);
      } catch (e) {
        console.error('restoreScheduledReminders: failed scheduling single reminder', e, r);
      }
    }
  } catch (e) {
    console.error('restoreScheduledReminders: fetch failed', e);
    // network or backend error: leave existing scheduled notifications untouched
  }
}

/** make register async and await initial restore so callers can wait for scheduling to complete */
export async function registerAndScheduleForUser(userId: number) {
  // make sure foreground notifications are shown
  Notifications.setNotificationHandler({
    handleNotification: async () => ({
      shouldShowAlert: true,
      shouldPlaySound: true,
      shouldSetBadge: true,
      shouldShowBanner: true,
      shouldShowList: true,
    }),
  });

  // when user taps the notification, refresh scheduled reminders from server
  Notifications.addNotificationResponseReceivedListener(async () => {
    console.log('Notification tapped: refreshing scheduled reminders');
    await restoreScheduledReminders(userId).catch((e) => console.error('tap listener restore failed', e));
  });

  // refresh when app becomes active
  AppState.addEventListener('change', (state) => {
    if (state === 'active') {
      console.log('App became active: refreshing scheduled reminders');
      restoreScheduledReminders(userId).catch((e) => console.error('AppState restore failed', e));
    }
  });

  // initial pass — await it so callers (App.tsx) see scheduling completed
  await restoreScheduledReminders(userId);
}

export async function getAllLocalMappings(): Promise<Record<string, string>> {
  try {
    const keys = await AsyncStorage.getAllKeys();
    const notifKeys = keys.filter((k: string) => k.startsWith('notif:'));
    const values = await AsyncStorage.multiGet(notifKeys);
    const out: Record<string, string> = {};
    for (const [k, v] of values) {
      if (k && v) out[k.replace('notif:', '')] = v;
    }
    return out;
  } catch (e) {
    return {};
  }
}
