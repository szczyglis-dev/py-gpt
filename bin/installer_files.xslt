<?xml version="1.0" encoding="UTF-8"?>
<!-- heat output for a per-user MSI: registry key paths and explicit cleanup. -->
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:w="http://schemas.microsoft.com/wix/2006/wi"
                xmlns="http://schemas.microsoft.com/wix/2006/wi" exclude-result-prefixes="w">
  <xsl:output method="xml" indent="yes" encoding="utf-8" />
  <xsl:template match="@*|node()">
    <xsl:copy><xsl:apply-templates select="@*|node()" /></xsl:copy>
  </xsl:template>
  <xsl:template match="w:File/@KeyPath">
    <xsl:attribute name="KeyPath">no</xsl:attribute>
  </xsl:template>
  <xsl:template match="w:File[@Source='$(var.SourceDir)\pygpt.exe']/@Id">
    <xsl:attribute name="Id">PygptExe</xsl:attribute>
  </xsl:template>
  <!-- heat IDs contain a stable 32-digit hash. Mixed file/registry components
       require an explicit GUID rather than WiX's automatic GUID generation. -->
  <xsl:template match="w:Component[w:File]/@Guid">
    <xsl:variable name="hash" select="substring(../@Id, 4)" />
    <xsl:attribute name="Guid"><xsl:value-of select="concat(substring($hash,1,8),'-',substring($hash,9,4),'-',substring($hash,13,4),'-',substring($hash,17,4),'-',substring($hash,21,12))" /></xsl:attribute>
  </xsl:template>
  <xsl:template match="w:Component">
    <xsl:copy>
      <xsl:apply-templates select="@*|node()" />
      <RegistryValue Root="HKCU" Key="Software\PyGPT\Installer\Files"
                     Name="{@Id}" Type="integer" Value="1" KeyPath="yes" />
    </xsl:copy>
  </xsl:template>
  <xsl:template match="w:Directory">
    <xsl:copy>
      <xsl:apply-templates select="@*|node()" />
      <Component Id="cleanup_{@Id}" Guid="*">
        <RegistryValue Root="HKCU" Key="Software\PyGPT\Installer\Directories"
                       Name="{@Id}" Type="integer" Value="1" KeyPath="yes" />
        <RemoveFolder Id="remove_{@Id}" On="uninstall" />
        <!-- Only generated Python bytecode, not arbitrary user files. -->
        <RemoveFile Id="bytecode_{@Id}" Name="*.pyc" On="uninstall" />
      </Component>
    </xsl:copy>
  </xsl:template>
  <xsl:template match="w:ComponentGroup">
    <xsl:copy>
      <xsl:apply-templates select="@*|node()" />
      <xsl:for-each select="//w:Directory">
        <ComponentRef Id="cleanup_{@Id}" />
      </xsl:for-each>
    </xsl:copy>
  </xsl:template>
</xsl:stylesheet>
