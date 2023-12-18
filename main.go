package main

import (
    "fmt"
	"log"
    "os"
    "os/signal"
    "syscall"
	"discordbot/src"
    "github.com/bwmarrin/discordgo"
	"strings"
)

func main() {
    botToken := "TOOOOOOOOOOOOOOOOOOKEEEEEEN" // Reemplaza esto con el token de tu bot

	// Crear un archivo de registro (log file)
	logFile, err := os.OpenFile("bot.log", os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0666)
	if err != nil {
		log.Fatal("Error al abrir/crear el archivo de log:", err)
	}
	defer logFile.Close()
	// Configurar el logger para que escriba en el archivo
    log.SetOutput(logFile)

    // Crea una nueva sesión de DiscordGo
    dg, err := discordgo.New("Bot " + botToken)
    if err != nil {
        fmt.Println("Error al crear la sesión de Discord:", err)
		log.Fatalf("Error al crear la sesión de Discord:", err)
        return
    }

    // Mapea los comandos con las funciones correspondientes
    commandMap := map[string]func(s *discordgo.Session, m *discordgo.MessageCreate){
        ">saludo":   discordbot.Saludar,
        ">info":     discordbot.Informacion,
        ">usuarios": discordbot.MostrarUsuarios,
		">ping": discordbot.Ping,
		">rick": discordbot.Rick,
    }

    // Agrega un evento de mensaje
    dg.AddHandler(func(s *discordgo.Session, m *discordgo.MessageCreate) {
        // Ignora los mensajes del bot mismo
        if m.Author.ID == s.State.User.ID {
            return
        }

        // Verifica si el mensaje es un comando
        if commandFunc, ok := commandMap[m.Content]; ok {
            commandFunc(s, m)
        }else if strings.HasPrefix(m.Content, ">") {
            // Si el mensaje es un comando pero no está en el commandMap, es un comando desconocido
            mensaje := fmt.Sprintf("El comando '%s' no existe. Introduce un comando válido.", m.Content)
			log.Println("El usuario "+m.Author.Username+" intento usar el comando "+m.Content+".")
            s.ChannelMessageSend(m.ChannelID, mensaje)
        }
    })

    // Abre la sesión de Discord
    err = dg.Open()
    if err != nil {
        fmt.Println("Error al abrir la conexión de Discord:", err)
		log.Fatalf("Error al abrir la conexión de Discord:", err)
        return
    }

    fmt.Println("El bot está en funcionamiento. Presiona Ctrl + C para detenerlo.")
    log.Println("El bot está en funcionamiento. Presiona Ctrl + C para detenerlo.")

    // Espera hasta que se presione Ctrl + C para cerrar el bot
    sc := make(chan os.Signal, 1)
    signal.Notify(sc, syscall.SIGINT, syscall.SIGTERM, os.Interrupt, os.Kill)
    <-sc
	log.Println("Bot cerrado.")
    // Cierra la sesión de Discord antes de salir
    dg.Close()
}

