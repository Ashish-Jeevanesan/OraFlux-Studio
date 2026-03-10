// frontend/src/app/services/session.service.ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, of } from 'rxjs';
import { catchError, tap, shareReplay } from 'rxjs/operators';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root',
})
export class SessionService {
  private apiUrl = environment.apiUrl;
  private sessionIdSubject = new BehaviorSubject<string | null>(null);
  
  // Public observable for components to subscribe to session ID changes
  sessionId$ = this.sessionIdSubject.asObservable();

  constructor(private http: HttpClient) {}

  /**
   * Starts a new session if one doesn't exist.
   * Caches the result to avoid multiple calls.
   */
  startSession(): Observable<{ sessionId: string }> {
    if (this.sessionIdSubject.value) {
        return of({ sessionId: this.sessionIdSubject.value });
    }
    
    return this.http.post<{ sessionId: string }>(`${this.apiUrl}/session/start`, {}).pipe(
      tap((response) => {
        this.sessionIdSubject.next(response.sessionId);
        console.log('Session started:', response.sessionId);
      }),
      catchError((err) => {
        console.error('Failed to start session', err);
        this.sessionIdSubject.next(null);
        throw err; // Re-throw the error to be handled by the caller
      }),
      shareReplay(1) // Cache the last emitted value
    );
  }

  /**
   * Gets the current session ID synchronously.
   * Throws an error if the session has not been started.
   */
  getSessionId(): string {
    const sessionId = this.sessionIdSubject.value;
    if (!sessionId) {
      throw new Error('Session not started. Call startSession() first.');
    }
    return sessionId;
  }

  /**
   * Closes the current session on the backend.
   */
  closeSession(): Observable<any> {
    const sessionId = this.getSessionId();
    this.sessionIdSubject.next(null); // Clear session ID on the client immediately
    return this.http.post(`${this.apiUrl}/session/close`, { sessionId });
  }
}
