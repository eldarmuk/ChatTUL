import { HttpClient, HttpEvent, HttpHandler, HttpHandlerFn, HttpHeaders, HttpRequest } from "@angular/common/http";
import { inject, Injectable } from "@angular/core";
import { BehaviorSubject, Observable, tap } from 'rxjs';
import { environment } from "../environments/environment";


export interface Session {
  token: string;
  conversation_id: string;
}

const httpOptions = {
  headers: new HttpHeaders({
    "Content-Type": "application/json"
  })
};


@Injectable({ providedIn: 'root' })
export class SessionService {
  private readonly http = inject(HttpClient);

  session: BehaviorSubject<Session | undefined> = new BehaviorSubject<Session | undefined>(undefined);

  beginSession(): Observable<Session> {
    this.endSession();

    return this.http.post<Session>(
      `${environment.API_URL}/new-session`,
      null,
      httpOptions,
    ).pipe(
      tap({
        next: (session) => this.session.next(session),
        error: (err) => console.error("failed to start new session", err)
      })
    )
  }

  endSession() {
    this.session.complete();
    this.session = new BehaviorSubject<Session | undefined>(undefined);
  }

}

export function sessionInterceptor(req: HttpRequest<unknown>, next: HttpHandlerFn): Observable<HttpEvent<unknown>> {
  const sessionService = inject(SessionService);

  const session = sessionService.session.value;

  if (session) {
    const req_url = new URL(req.url);
    const api_url = new URL(environment.API_URL);

    if (req_url.hostname == api_url.hostname) {
      req.headers.set("Authorization", `Bearer ${session.token}`);
    }
  }

  return next(req);
}


