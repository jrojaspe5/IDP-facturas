import subprocess
import sys
import streamlit as st

@st.cache_resource
def install_boto3():
# Importación condicional de boto3
subprocess.check_call([sys.executable, "-m", "pip", "install", "boto3"])

try:
    import boto3
except ImportError:
    install_boto3()
    import boto3

# Configuración de página
st.set_page_config(
    page_title="Procesador de Facturas IDP",
    page_icon="🧾",
    layout="wide"
)

# Autenticación simple por email
def check_authentication():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        st.title("🔐 Acceso Restringido")
        
        email = st.text_input("Email autorizado:")
        password = st.text_input("Contraseña:", type="password")
        
        authorized_emails = [
            'luisauryechenique07@gmail.com',
            'josem155@gmail.com'
        ]
        
        if st.button("Iniciar Sesión"):
            if email in authorized_emails and len(password) >= 8:
                st.session_state.authenticated = True
                st.session_state.user_email = email
                st.rerun()
            else:
                st.error("❌ Email no autorizado o contraseña muy corta")
        
        st.info("Solo usuarios autorizados pueden acceder a esta aplicación")
        st.stop()

# Configurar AWS con credenciales de Streamlit Secrets
def setup_aws():
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"],
            aws_session_token=st.secrets.get("AWS_SESSION_TOKEN"),
            region_name=st.secrets.get("AWS_DEFAULT_REGION", "us-east-1")
        )
        return s3_client
    except Exception as e:
        st.error(f"❌ Error configurando AWS: {str(e)}")
        st.info("Configura las credenciales AWS en Streamlit Secrets")
        st.stop()

# Verificar autenticación
check_authentication()

# Configurar AWS
s3_client = setup_aws()

# Variables de configuración
INPUT_BUCKET = st.secrets.get("INPUT_BUCKET", "idp-facturas-input-XX")
OUTPUT_BUCKET = st.secrets.get("OUTPUT_BUCKET", "idp-facturas-output-XX")

# Interfaz principal
st.title("🧾 Procesador Inteligente de Facturas")
st.write(f"**Usuario:** {st.session_state.user_email}")

if st.button("🚪 Cerrar Sesión", type="secondary"):
    st.session_state.authenticated = False
    st.rerun()

col1, col2 = st.columns([1, 1])

with col1:
    st.header("📤 Subir Factura")
    
    uploaded_file = st.file_uploader(
        "Selecciona una factura (PDF, PNG, JPG)",
        type=['pdf', 'png', 'jpg', 'jpeg'],
        help="Sube facturas de proveedores para extraer información automáticamente"
    )
    
    if uploaded_file:
        st.success(f"Archivo cargado: {uploaded_file.name}")
        
        if st.button("🚀 Procesar Factura", type="primary"):
            try:
                with st.spinner("Subiendo archivo a S3..."):
                    file_key = f"facturas/{uploaded_file.name}"
                    s3_client.upload_fileobj(
                        uploaded_file,
                        INPUT_BUCKET,
                        file_key
                    )
                
                st.success("✅ Archivo subido a S3. Procesando...")
                st.info("La Lambda se ejecutará automáticamente. Revisa los resultados en unos minutos.")
                
            except ClientError as e:
                if 'ExpiredToken' in str(e):
                    st.error("🔑 Token AWS expirado. Contacta al administrador.")
                else:
                    st.error(f"❌ Error AWS: {str(e)}")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

with col2:
    st.header("📊 Resultados Procesados")
    
    if st.button("🔄 Actualizar Resultados"):
        try:
            with st.spinner("Cargando resultados..."):
                response = s3_client.list_objects_v2(
                    Bucket=OUTPUT_BUCKET,
                    Prefix="resultados/"
                )
                
                if 'Contents' in response:
                    files = [obj['Key'] for obj in response['Contents'] if obj['Key'].endswith('.csv')]
                    
                    if files:
                        selected_file = st.selectbox("Selecciona un resultado:", files)
                        
                        if selected_file:
                            # Descargar y mostrar CSV
                            obj = s3_client.get_object(Bucket=OUTPUT_BUCKET, Key=selected_file)
                            df = pd.read_csv(BytesIO(obj['Body'].read()))
                            
                            st.subheader("📋 Datos Extraídos")
                            st.dataframe(df, use_container_width=True)
                            
                            # Botón de descarga
                            csv_buffer = BytesIO()
                            df.to_csv(csv_buffer, index=False)
                            st.download_button(
                                "💾 Descargar CSV",
                                csv_buffer.getvalue(),
                                file_name=f"factura_procesada_{selected_file.split('/')[-1]}",
                                mime="text/csv"
                            )
                    else:
                        st.info("No hay resultados procesados aún.")
                else:
                    st.info("No hay archivos en el bucket de resultados.")
                    
        except ClientError as e:
            if 'ExpiredToken' in str(e):
                st.error("🔑 Token AWS expirado. Contacta al administrador.")
            else:
                st.error(f"❌ Error AWS: {str(e)}")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

# Sidebar con información
with st.sidebar:
    st.header("ℹ️ Información del Sistema")
    st.write(f"**Bucket Input:** {INPUT_BUCKET}")
    st.write(f"**Bucket Output:** {OUTPUT_BUCKET}")
    
    st.header("📝 Campos Extraídos")
    st.write("""
    - Número de factura
    - Fecha de emisión
    - Proveedor
    - Total
    - Subtotal
    - Impuestos
    - Items de la tabla
    """)
    
    st.header("👥 Usuarios Autorizados")
    st.write("- ")
    st.write("- ")
