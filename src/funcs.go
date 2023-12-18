package discordbot
import (
    "fmt"
    "github.com/bwmarrin/discordgo"
	"os"
	"log"
)
// Funciones de comandos
func Saludar(s *discordgo.Session, m *discordgo.MessageCreate) {
    s.ChannelMessageSend(m.ChannelID, "¡Hola! Que viva la saltisima trinidad, aqui el admin abuse no existe")
}

func Informacion(s *discordgo.Session, m *discordgo.MessageCreate) {
    s.ChannelMessageSend(m.ChannelID, "¡Este es un bot creado con DiscordGo en GoLang!")
}

func MostrarUsuarios(s *discordgo.Session, m *discordgo.MessageCreate) {
    // Obtenemos la lista de miembros del servidor
    guildMembers, err := s.GuildMembers(m.GuildID, "", 1000)
    if err != nil {
        s.ChannelMessageSend(m.ChannelID, "Error al obtener la lista de usuarios.")
        return
    }

    totalUsers := len(guildMembers)
    s.ChannelMessageSend(m.ChannelID, fmt.Sprintf("El servidor tiene %d usuarios.", totalUsers))
}

func Ping(s *discordgo.Session, m *discordgo.MessageCreate){
	s.ChannelMessageSend(m.ChannelID, "Pong")
}

func Rick(s *discordgo.Session, m *discordgo.MessageCreate){
	file, err := os.Open("img/ric.jpg") // Reemplaza con la ruta de tu imagen
			if err != nil {
				log.Fatalf("Error al abrir el archivo:", err)
				return
			}
			defer file.Close()

			// Enviar el archivo al canal
			_, err = s.ChannelFileSend(m.ChannelID, "nombre_imagen.jpg", file)
			if err != nil {
				log.Fatalf("Error al enviar la imagen:", err)
				return
			}
}
