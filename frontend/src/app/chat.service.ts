import { inject, Injectable } from "@angular/core";
import { Session, SessionService } from "./session.service";
import { BehaviorSubject, Observable, Subject, throwError } from "rxjs";
import { io, Socket } from "socket.io-client";
import { environment } from "../environments/environment";

export interface Message {
  id: number,
  text: string,
  botMessage: boolean,
  rating: number,
};

export const USER_UTTERED = "user_uttered";
export const BOT_UTTERED = "bot_uttered";

@Injectable({ providedIn: 'root' })
export class ChatService {
  private readonly sessionService = inject(SessionService);

  messages = new BehaviorSubject<Message[]>([]);
  botMessage$ = new Subject<string>();

  private _socket: Socket | undefined = undefined;
  private _conversation_id: string | undefined;

  connect(session: Session): Observable<Socket> {
    return new Observable<Socket>((subscriber) => {
      const socket = io(environment.SOCKET_API_URL, {
        path: environment.SOCKET_IO_PATH,
        auth: { token: session.token }
      });

      socket.on("connect", () => {
        this.messages.next([
          {
            id: Date.now(),
            text: "Hi! I'm ChatTUL, your AI assistant for all things related to recruitment at Lodz University of Technology.\n\nWhether you're a prospective student exploring your options or a first-year student looking for guidance, I'm here to help.\n\nFeel free to ask me anything about recruitment at Lodz University of Technology!",
            botMessage: true,
            rating: 0
          }
        ]);
        subscriber.next(socket);
        this._socket = socket;
        this._conversation_id = session.conversation_id;
      });

      socket.on("connect_error", (err) => {
        subscriber.error(err);
        subscriber.complete();
      });

      socket.on("disconnect", () => {
        subscriber.complete();
      });

      socket.on(BOT_UTTERED, (utterance) => {
        this.botMessage$.next(utterance.text);
      });
    });
  }

  disconnect() {
    if (this._socket) {
      this._socket.disconnect();
      this._socket = undefined;
    }
  }
  
  sendMessage(text: string) {
    this._socket?.emit(USER_UTTERED, { message: text, session_id: this._conversation_id });
    // Simulate bot response with Markdown-friendly, soft text
    setTimeout(() => {
      this.botMessage$.next(
        "The main campuses of **Łódź University of Technology** are located on *Stefana Żeromskiego street*.\n\nIf you'd like to explore, you can gently use [naviPŁ](https://mapa.p.lodz.pl/) to see for yourself. 😊"
      );
    }, 300); // simulate slight delay
    // Optionally, you can still emit to socket if needed:
    // this._socket?.emit(USER_UTTERED, { message: text, session_id: this._conversation_id });
  }
}
